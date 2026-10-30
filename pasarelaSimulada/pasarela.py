# Pasarela de pago simulada. Funciona como Webpay: el comprador paga en la página de
# la pasarela, no en la tienda, así los datos de la tarjeta nunca pasan por la tienda.
# Corre aparte del servicio de compras, en el puerto 8001. Todo vive en memoria: si se
# reinicia, se borran las transacciones y las tarjetas vuelven a como partieron.
#
# El flujo, igual que una pasarela real:
#   1. El comercio crea la transacción (POST /transacciones, servidor a servidor) y
#      recibe un token y la URL donde paga el comprador.
#   2. El comprador entra a /pagar/{token} y elige crédito o débito.
#      Crédito: número, vencimiento y CVV. 3 CVV malos bloquean la tarjeta.
#      Débito: número y después el login del banco (RUT y clave). 3 claves malas
#      bloquean al usuario del banco.
#      Si se aprueba, el monto queda RETENIDO en la tarjeta, todavía no se cobra.
#   3. La pasarela devuelve al comprador al comercio (url_retorno?token_ws=...).
#   4. El comercio confirma (POST /transacciones/{token}/confirmar, servidor a
#      servidor). Recién ahí se cobra. Si nadie confirma a tiempo, la retención se
#      devuelve sola: la plata vuelve a la tarjeta y no hay cobro.
#
# Tiempos: el comprador tiene SEGUNDOS_PAGO para pagar (o menos, si el comercio manda
# un "pagar_antes_de" más cercano: así la transacción vence antes que la reserva de
# stock). Después de aprobar, el comercio tiene SEGUNDOS_CONFIRMAR para confirmar.
#
# Idempotencia: crear y confirmar llevan Idempotency-Key. Si la misma clave llega otra
# vez se devuelve lo mismo que la primera vez y no se cobra de nuevo. Una transacción
# además se aprueba una sola vez: el doble clic en "Pagar" no retiene dos veces.
#
# Hilos: uvicorn atiende cada solicitud en un hilo aparte, por eso todo cambio de
# estado se hace con el candado tomado.
#
# Modos (PUT /simulacion), afectan solo a lo que llama el servicio de pagos:
#   normal -> responde al tiro
#   lenta  -> se demora 5 segundos (para ver el tiempo límite y el Circuit Breaker)
#   falla  -> da error 503, como si estuviera caída

import os
import random
import threading
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

SEGUNDOS_PAGO = int(os.environ.get("PASARELA_SEGUNDOS_PAGO", 300))
SEGUNDOS_CONFIRMAR = int(os.environ.get("PASARELA_SEGUNDOS_CONFIRMAR", 60))
INTENTOS_MAXIMOS = 3
URL_PUBLICA = os.environ.get("PASARELA_URL_PUBLICA", "http://127.0.0.1:8001")
PAGINA = Path(__file__).with_name("pagina_pago.html")

candado = threading.Lock()


def _con_digito_verificador(base: str) -> str:
    """Agrega el dígito de Luhn, el mismo que traen las tarjetas de verdad."""
    suma = 0
    for i, digito in enumerate(reversed(base)):
        n = int(digito) * (2 if i % 2 == 0 else 1)
        suma += n - 9 if n > 9 else n
    return base + str((10 - suma % 10) % 10)


def _luhn_valido(numero: str) -> bool:
    return numero.isdigit() and 13 <= len(numero) <= 19 and _con_digito_verificador(numero[:-1]) == numero


def _marca(numero: str) -> str:
    return {"4": "VISA", "5": "Mastercard", "3": "AMEX"}.get(numero[0], "Tarjeta")


def _normalizar_rut(rut: str) -> str:
    return rut.replace(".", "").replace("-", "").replace(" ", "").upper()


@dataclass
class Tarjeta:
    numero: str
    tipo: str  # credito | debito
    vencimiento: str  # MM/AA
    cvv: str
    saldo: int  # cupo disponible (crédito) o saldo de la cuenta (débito)
    caso: str = ""  # para qué sirve como tarjeta de prueba
    rut: str | None = None  # débito: usuario del banco
    clave_banco: str | None = None
    intentos_cvv: int = 0
    intentos_banco: int = 0
    bloqueada: bool = False  # por 3 CVV malos
    banco_bloqueado: bool = False  # por 3 claves malas

    def vencida(self) -> bool:
        mes, anio = self.vencimiento.split("/")
        hoy = datetime.now()
        return (2000 + int(anio), int(mes)) < (hoy.year, hoy.month)

    def medio(self) -> str:
        tipo = "Crédito" if self.tipo == "credito" else "Débito"
        return f"{tipo} {_marca(self.numero)} ****{self.numero[-4:]}"


@dataclass
class Transaccion:
    token: str
    pedido_id: int
    monto: int
    url_retorno: str
    vence: float  # hasta cuándo puede pagar el comprador (time.time())
    estado: str = "pendiente"  # pendiente | banco | autorizada | rechazada | cobrada
    tarjeta: Tarjeta | None = None
    motivo: str | None = None
    autorizada_en: float | None = None
    codigo: str | None = None


def _tarjetas_demo() -> dict[str, Tarjeta]:
    """Las tarjetas de prueba que se muestran en la página de pago (como en el ambiente de
    integración de una pasarela real). Todas con CVV 123."""
    lista = [
        Tarjeta(_con_digito_verificador("411111111111111"), "credito", "12/29", "123", 3_000_000, "Crédito: se aprueba"),
        Tarjeta(_con_digito_verificador("555555555555444"), "credito", "12/29", "123", 0, "Crédito: cupo insuficiente"),
        Tarjeta(_con_digito_verificador("400000000000000"), "credito", "03/24", "123", 3_000_000, "Crédito: vencida"),
        Tarjeta(_con_digito_verificador("400005665566555"), "debito", "12/29", "123", 2_000_000, "Débito: se aprueba",
                rut="111111111", clave_banco="1234"),
        Tarjeta(_con_digito_verificador("520082828282821"), "debito", "12/29", "123", 0, "Débito: saldo insuficiente",
                rut="222222222", clave_banco="1234"),
    ]
    return {t.numero: t for t in lista}


_estado = {"modo": os.environ.get("PASARELA_MODO", "normal")}
_tarjetas: dict[str, Tarjeta] = _tarjetas_demo()
_transacciones: dict[str, Transaccion] = {}
_respuestas: dict[str, dict] = {}  # Idempotency-Key -> respuesta que ya se dio
_cobros: list[dict] = []  # lo que de verdad se cobró
# Llamadas del servicio de pagos (crear y confirmar). Con el Circuit Breaker abierto
# casi no llegan, aunque haya muchos pagos esperando: eso muestra la simulación.
_llamadas = {"recibidas": 0, "rechazadas": 0}


def _rechazar(t: Transaccion, motivo: str) -> None:
    t.estado, t.motivo = "rechazada", motivo


def _revisar_tiempos(t: Transaccion, ahora: float) -> None:
    """Vencimientos. Se llama con el candado tomado, cada vez que se toca la transacción
    y también desde el hilo de fondo (por si nadie la vuelve a tocar)."""
    if t.estado in ("pendiente", "banco") and ahora > t.vence:
        _rechazar(t, "Se acabó el tiempo para pagar.")
    elif t.estado == "autorizada" and ahora > t.autorizada_en + SEGUNDOS_CONFIRMAR:
        t.tarjeta.saldo += t.monto  # se devuelve la retención: no hubo cobro
        _rechazar(t, "El comercio no confirmó a tiempo. No se hizo ningún cobro.")


def _vigilar_vencimientos(detener: threading.Event) -> None:
    while not detener.wait(2):
        with candado:
            ahora = time.time()
            for t in _transacciones.values():
                _revisar_tiempos(t, ahora)


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    detener = threading.Event()
    threading.Thread(target=_vigilar_vencimientos, args=(detener,), daemon=True).start()
    yield
    detener.set()


app = FastAPI(title="Pasarela simulada", lifespan=ciclo_de_vida)


def _simular_modo() -> None:
    """Solo para lo que llama el servicio de pagos (crear y confirmar)."""
    modo = _estado["modo"]
    with candado:
        _llamadas["recibidas"] += 1
        if modo == "falla":
            _llamadas["rechazadas"] += 1
    if modo == "falla":
        raise HTTPException(503, "Pasarela caída")
    if modo == "lenta":
        time.sleep(5)


def _respuesta_previa(clave: str) -> dict | None:
    """Un reintento con una clave ya procesada se responde al tiro, aunque la pasarela
    esté lenta: así el reintento del servicio de pagos recibe lo que ya se hizo."""
    with candado:
        return _respuestas.get(clave)


def _buscar(token: str) -> Transaccion:
    t = _transacciones.get(token)
    if t is None:
        raise HTTPException(404, "La transacción no existe.")
    _revisar_tiempos(t, time.time())
    return t


def _vista(t: Transaccion, error: str | None = None) -> dict:
    """Lo que ve la página de pago. Nunca incluye el número completo ni el CVV."""
    intentos = None
    if t.tarjeta and t.estado == "banco":
        intentos = INTENTOS_MAXIMOS - t.tarjeta.intentos_banco
    return {
        "token": t.token,
        "comercio": "KYRO",
        "pedido_id": t.pedido_id,
        "monto": t.monto,
        "estado": t.estado,
        "segundos_restantes": max(0, int(t.vence - time.time())),
        "medio": t.tarjeta.medio() if t.tarjeta else None,
        "motivo": t.motivo,
        "error": error,
        "intentos_restantes": intentos,
        "url_retorno": f"{t.url_retorno}?token_ws={t.token}",
    }


def _autorizar(t: Transaccion) -> None:
    """Retiene el monto en la tarjeta. El cobro de verdad es al confirmar."""
    tarjeta = t.tarjeta
    if tarjeta.saldo < t.monto:
        _rechazar(t, "Cupo insuficiente." if tarjeta.tipo == "credito" else "Saldo insuficiente.")
        return
    tarjeta.saldo -= t.monto
    t.estado, t.autorizada_en, t.codigo = "autorizada", time.time(), "AUT-" + uuid.uuid4().hex[:10].upper()


# --- Comercio (servidor a servidor) -------------------------------------------------


class NuevaTransaccion(BaseModel):
    pedido_id: int
    monto: int = Field(gt=0)
    url_retorno: str
    pagar_antes_de: float | None = None  # epoch: el comercio puede acortar el plazo


@app.post("/transacciones", summary="Crear transacción (comercio)")
def crear_transaccion(datos: NuevaTransaccion, clave: str = Header(alias="Idempotency-Key")):
    if (previa := _respuesta_previa(clave)) is not None:
        return previa
    _simular_modo()
    with candado:
        if clave in _respuestas:
            return _respuestas[clave]
        vence = time.time() + SEGUNDOS_PAGO
        if datos.pagar_antes_de:
            vence = min(vence, datos.pagar_antes_de)
        t = Transaccion(uuid.uuid4().hex, datos.pedido_id, datos.monto, datos.url_retorno, vence)
        _transacciones[t.token] = t
        respuesta = {"token": t.token, "url": f"{URL_PUBLICA}/pagar/{t.token}"}
        _respuestas[clave] = respuesta
        return respuesta


@app.post("/transacciones/{token}/confirmar", summary="Confirmar y cobrar (comercio)")
def confirmar(token: str, clave: str = Header(alias="Idempotency-Key")):
    if (previa := _respuesta_previa(clave)) is not None:
        return previa
    _simular_modo()
    with candado:
        if clave in _respuestas:
            return _respuestas[clave]
        t = _buscar(token)
        if t.estado in ("pendiente", "banco"):
            # El comprador no terminó (o alguien inventó la vuelta): se cierra sin cobrar.
            _rechazar(t, "El pago no se completó.")
        if t.estado == "autorizada":
            t.estado = "cobrada"
            _cobros.append({"clave": clave, "token": token, "pedido_id": t.pedido_id, "monto": t.monto})
        if t.estado == "cobrada":
            respuesta = {"autorizado": True, "referencia": t.codigo, "medio": t.tarjeta.medio(), "motivo": None}
        else:
            medio = t.tarjeta.medio() if t.tarjeta else None
            respuesta = {"autorizado": False, "referencia": None, "medio": medio, "motivo": t.motivo}
        _respuestas[clave] = respuesta
        return respuesta


# --- Comprador (lo que usa la página de pago) ---------------------------------------


@app.get("/pagar/{token}", response_class=HTMLResponse, summary="Página de pago")
def pagina_de_pago(token: str):
    return PAGINA.read_text(encoding="utf-8")


@app.get("/transacciones/{token}", summary="Ver transacción")
def ver_transaccion(token: str):
    with candado:
        return _vista(_buscar(token))


class DatosTarjeta(BaseModel):
    tipo: Literal["credito", "debito"]
    numero: str = Field(max_length=30)
    vencimiento: str = Field(default="", max_length=5)
    cvv: str = Field(default="", max_length=4)


@app.post("/transacciones/{token}/tarjeta", summary="Pagar con tarjeta")
def pagar_con_tarjeta(token: str, datos: DatosTarjeta):
    with candado:
        t = _buscar(token)
        if t.estado != "pendiente":
            return _vista(t)  # doble clic o pestaña vieja: ya se resolvió
        numero = datos.numero.replace(" ", "").replace("-", "")
        if not _luhn_valido(numero):
            return _vista(t, "El número de tarjeta no es válido.")
        tarjeta = _tarjetas.get(numero)
        if tarjeta is None:
            return _vista(t, "El banco emisor no reconoce esta tarjeta.")
        if tarjeta.tipo != datos.tipo:
            return _vista(t, f"Esta tarjeta es de {'crédito' if tarjeta.tipo == 'credito' else 'débito'}.")
        t.tarjeta = tarjeta

        if tarjeta.tipo == "debito":
            if tarjeta.banco_bloqueado:
                _rechazar(t, "Tu usuario del banco está bloqueado por intentos fallidos.")
            else:
                t.estado = "banco"  # ahora pide RUT y clave del banco
            return _vista(t)

        if tarjeta.bloqueada:
            _rechazar(t, "Tarjeta bloqueada por ingresar mal el CVV 3 veces. Contacta a tu banco.")
        elif tarjeta.vencida():
            _rechazar(t, "Tarjeta vencida.")
        elif datos.vencimiento != tarjeta.vencimiento:
            return _vista(t, "La fecha de vencimiento no coincide.")
        elif datos.cvv != tarjeta.cvv:
            tarjeta.intentos_cvv += 1
            quedan = INTENTOS_MAXIMOS - tarjeta.intentos_cvv
            if quedan > 0:
                return _vista(t, f"CVV incorrecto. Te quedan {quedan} intento{'s' if quedan > 1 else ''}.")
            tarjeta.bloqueada = True
            _rechazar(t, "Ingresaste mal el CVV 3 veces: la tarjeta quedó bloqueada.")
        else:
            tarjeta.intentos_cvv = 0
            _autorizar(t)
        return _vista(t)


class DatosBanco(BaseModel):
    rut: str = Field(max_length=15)
    clave: str = Field(max_length=30)


@app.post("/transacciones/{token}/banco", summary="Login del banco (débito)")
def login_banco(token: str, datos: DatosBanco):
    with candado:
        t = _buscar(token)
        if t.estado != "banco":
            return _vista(t)
        tarjeta = t.tarjeta
        if _normalizar_rut(datos.rut) != tarjeta.rut or datos.clave != tarjeta.clave_banco:
            tarjeta.intentos_banco += 1
            quedan = INTENTOS_MAXIMOS - tarjeta.intentos_banco
            if quedan > 0:
                return _vista(t, f"RUT o clave incorrectos. Te quedan {quedan} intento{'s' if quedan > 1 else ''}.")
            tarjeta.banco_bloqueado = True
            _rechazar(t, "Ingresaste mal la clave 3 veces: tu usuario del banco quedó bloqueado.")
        else:
            tarjeta.intentos_banco = 0
            _autorizar(t)
        return _vista(t)


@app.post("/transacciones/{token}/anular", summary="El comprador anula")
def anular(token: str):
    with candado:
        t = _buscar(token)
        if t.estado in ("pendiente", "banco"):
            _rechazar(t, "Anulaste la compra.")
        return _vista(t)


@app.get("/tarjetas-prueba", summary="Tarjetas de prueba")
def tarjetas_prueba():
    def formatear_rut(rut: str) -> str:
        return f"{int(rut[:-1]):,}".replace(",", ".") + "-" + rut[-1]

    return [
        {"caso": t.caso, "tipo": t.tipo, "numero": t.numero, "vencimiento": t.vencimiento, "cvv": t.cvv,
         "rut": formatear_rut(t.rut) if t.rut else None, "clave_banco": t.clave_banco}
        for t in _tarjetas_demo().values()
    ]


# --- Para pruebas y simulaciones ----------------------------------------------------


@app.get("/cobros", summary="Ver cobros")
def ver_cobros():
    return {"total": len(_cobros), "cobros": _cobros}


class Modo(BaseModel):
    modo: Literal["normal", "lenta", "falla"]


@app.get("/simulacion", summary="Ver modo")
def ver_modo():
    return {**_estado, **_llamadas}


@app.put("/simulacion", summary="Cambiar modo")
def cambiar_modo(nuevo: Modo):
    _estado["modo"] = nuevo.modo
    return {**_estado, **_llamadas}


class PedidoTarjeta(BaseModel):
    tipo: Literal["credito", "debito"]
    saldo: int = Field(ge=0)


@app.post("/simulacion/tarjetas", summary="Emitir tarjetas para una simulación")
def emitir_tarjetas(pedidos: list[PedidoTarjeta]):
    """Una tarjeta por comprador simulado, cada una con su saldo, CVV y usuario de banco."""
    azar = random.Random()
    emitidas = []
    with candado:
        for p in pedidos:
            while True:
                prefijo = "4" if azar.random() < 0.6 else "5" + str(azar.randint(1, 5))
                numero = _con_digito_verificador(prefijo + "".join(azar.choices("0123456789", k=15 - len(prefijo))))
                if numero not in _tarjetas:
                    break
            tarjeta = Tarjeta(numero, p.tipo, f"{azar.randint(1, 12):02d}/{azar.randint(28, 31)}",
                              f"{azar.randint(0, 999):03d}", p.saldo, "simulación")
            if p.tipo == "debito":
                tarjeta.rut = f"{azar.randint(5_000_000, 25_000_000)}{azar.choice('0123456789K')}"
                tarjeta.clave_banco = f"{azar.randint(0, 9999):04d}"
            _tarjetas[numero] = tarjeta
            emitidas.append({"numero": numero, "tipo": tarjeta.tipo, "vencimiento": tarjeta.vencimiento,
                             "cvv": tarjeta.cvv, "rut": tarjeta.rut, "clave_banco": tarjeta.clave_banco})
    return emitidas


@app.post("/simulacion/reiniciar", summary="Desbloquear y recargar las tarjetas de prueba")
def reiniciar():
    with candado:
        _tarjetas.update(_tarjetas_demo())
    return {"estado": "ok"}


@app.get("/salud", summary="Ver si está prendida")
def salud():
    return {"estado": "ok"}
