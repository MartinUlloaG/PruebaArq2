"""Pasarela de pago simulada: hace de servicio externo (como Webpay o Mercado Pago).

Corre en su propio proceso y no comparte nada con el servicio de compras.
Guarda los cobros en memoria: al reiniciarla se pierden, y está bien para una demo.

Idempotencia: cada autorización trae una clave (encabezado Idempotency-Key). Si la
misma clave llega dos veces, se devuelve la respuesta guardada y NO se cobra de nuevo.

Modos de simulación (se cambian en caliente con PUT /simulacion, o al arrancar con
la variable de entorno PASARELA_MODO):
  aprueba  -> autoriza todos los pagos
  rechaza  -> rechaza todos los pagos (como una tarjeta sin fondos)
  lenta    -> tarda más que el tiempo límite del servicio de compras y después autoriza
  falla    -> responde 503 sin cobrar (pasarela caída)
"""

import os
import threading
import time
import uuid
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

Modo = Literal["aprueba", "rechaza", "lenta", "falla"]
SEGUNDOS_MODO_LENTO = 5

app = FastAPI(title="Pasarela de pago simulada")

_candado = threading.Lock()  # los endpoints síncronos corren en varios hilos a la vez
_estado: dict = {"modo": os.environ.get("PASARELA_MODO", "aprueba")}
_respuestas: dict[str, dict] = {}  # clave de idempotencia -> respuesta ya entregada
_cobros: list[dict] = []  # solo los autorizados: es lo que se le cobró al cliente


class SolicitudAutorizacion(BaseModel):
    pedido_id: int
    monto: int = Field(ge=0)


class Autorizacion(BaseModel):
    autorizado: bool
    referencia: str | None
    motivo: str | None


class Simulacion(BaseModel):
    modo: Modo


@app.post("/autorizaciones", response_model=Autorizacion)
def autorizar(
    solicitud: SolicitudAutorizacion,
    clave: str = Header(alias="Idempotency-Key", min_length=1, max_length=100),
):
    with _candado:
        if clave in _respuestas:
            return _respuestas[clave]  # reintento: misma respuesta, sin cobrar otra vez
        modo = _estado["modo"]

    if modo == "falla":
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Pasarela no disponible.")
    if modo == "lenta":
        time.sleep(SEGUNDOS_MODO_LENTO)

    if modo == "rechaza":
        respuesta = {"autorizado": False, "referencia": None, "motivo": "Fondos insuficientes."}
    else:
        respuesta = {"autorizado": True, "referencia": f"AUT-{uuid.uuid4().hex[:10]}", "motivo": None}

    with _candado:
        if clave in _respuestas:  # otra solicitud con la misma clave ganó mientras tanto
            return _respuestas[clave]
        _respuestas[clave] = respuesta
        if respuesta["autorizado"]:
            _cobros.append({"clave": clave, "referencia": respuesta["referencia"], **solicitud.model_dump()})
    return respuesta


@app.get("/cobros")
def listar_cobros():
    """Para la demo: muestra que una misma clave genera un solo cobro."""
    with _candado:
        return {"total": len(_cobros), "cobros": list(_cobros)}


@app.get("/simulacion", response_model=Simulacion)
def ver_simulacion():
    return _estado


@app.put("/simulacion", response_model=Simulacion)
def cambiar_simulacion(simulacion: Simulacion):
    _estado["modo"] = simulacion.modo
    return _estado


@app.get("/salud")
def salud():
    return {"estado": "ok"}
