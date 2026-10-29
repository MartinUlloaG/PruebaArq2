"""Simulación: 100 clientes compran el mismo producto al mismo tiempo.

Usa el sistema de verdad (el backend levantado en el puerto 8000), igual que el navegador.
Muestra que se vende exactamente lo que hay, que nadie paga dos veces y que el sistema
sigue respondiendo durante la ráfaga.

Uso (con los servicios levantados), desde servicioCompras:
  python -m demostraciones.simulacion_100_usuarios            (stock 10)
  python -m demostraciones.simulacion_100_usuarios --stock 1  (la última unidad)
"""

import argparse
import statistics
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx

from app.infraestructura.base import Sesion
from app.infraestructura.repositorios import RepositorioInventario

API = "http://127.0.0.1:8000"
PASARELA = "http://127.0.0.1:8001"
CLAVE_CLIENTES = "Cliente-Demo-2026"
CLIENTES = ["cliente@demo.cl"] + [f"cliente{n:02d}@demo.cl" for n in range(1, 100)]


def titulo(texto: str) -> None:
    print(f"\n{'=' * 70}\n {texto}\n{'=' * 70}")


def entrar(http: httpx.Client, correo: str, clave: str) -> dict:
    r = http.post("/autenticacion/ingresar", json={"correo": correo, "clave": clave})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['token_acceso']}"}


def revisar_servicios(http: httpx.Client) -> None:
    for nombre, url in [("Servicio de compras", f"{API}/salud"), ("Pasarela de pago", f"{PASARELA}/salud")]:
        try:
            httpx.get(url, timeout=3).raise_for_status()
            print(f"  [OK] {nombre}")
        except httpx.HTTPError:
            raise SystemExit(f"  [X] {nombre} no responde. Levanta la tienda primero (Levantar tienda.bat).")
    httpx.put(f"{PASARELA}/simulacion", json={"modo": "aprueba"})
    print("  Pasarela en modo 'aprueba'.")


def dejar_stock(http: httpx.Client, operador: dict, producto: dict, stock: int) -> None:
    fila = next(f for f in http.get("/inventario", headers=operador).json() if f["producto_id"] == producto["producto_id"])
    diferencia = stock - fila["cantidad"]
    if diferencia:
        tipo = "ajuste_entrada" if diferencia > 0 else "ajuste_salida"
        http.patch(f"/inventario/{producto['producto_id']}", json={"cantidad": abs(diferencia), "tipo": tipo}, headers=operador).raise_for_status()
    print(f"  El operador dejó '{producto['nombre']}' con {stock} unidad(es).")


def vigilar(detener: threading.Event, resultados: dict) -> None:
    """Mientras dura la ráfaga, otro "usuario" sigue consultando: ¿el sistema responde?"""
    with httpx.Client(base_url=API, timeout=5) as http:
        while not detener.is_set():
            for ruta in ("/salud", "/catalogo/categorias"):
                try:
                    ok = http.get(ruta, headers=resultados["sesion"]).status_code == 200
                except httpx.HTTPError:
                    ok = False
                resultados["ok" if ok else "falla"] += 1
            time.sleep(0.05)


def main() -> None:
    parametros = argparse.ArgumentParser()
    parametros.add_argument("--stock", type=int, default=10)
    stock = parametros.parse_args().stock
    http = httpx.Client(base_url=API, timeout=30)

    titulo("1. Revisando que la tienda esté levantada")
    revisar_servicios(http)

    titulo("2. Preparando: 100 clientes inician sesión")
    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=20) as ejecutor:
        sesiones = list(ejecutor.map(lambda c: entrar(httpx.Client(base_url=API, timeout=30), c, CLAVE_CLIENTES), CLIENTES))
    print(f"  {len(sesiones)} sesiones con JWT en {time.perf_counter() - inicio:.1f} s")
    operador = entrar(http, "operador@demo.cl", "Operador-Demo-2026")
    producto = http.get("/catalogo", headers=sesiones[0]).json()[0]
    dejar_stock(http, operador, producto, stock)

    titulo(f"3. Los 100 clientes compran '{producto['nombre']}' al mismo tiempo")
    largada = threading.Barrier(len(sesiones))
    vigilancia = {"ok": 0, "falla": 0, "sesion": sesiones[0]}
    detener = threading.Event()
    vigia = threading.Thread(target=vigilar, args=(detener, vigilancia))
    vigia.start()

    def comprar(sesion: dict) -> tuple[int, float, dict]:
        with httpx.Client(base_url=API, timeout=30) as propio:
            largada.wait()  # todos parten en el mismo instante
            t = time.perf_counter()
            r = propio.post(
                "/pedidos",
                json={"items": [{"producto_id": producto["producto_id"], "cantidad": 1}]},
                headers={**sesion, "Idempotency-Key": uuid.uuid4().hex},
            )
            return r.status_code, time.perf_counter() - t, r.json()

    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=len(sesiones)) as ejecutor:
        respuestas = list(ejecutor.map(comprar, sesiones))
    duracion = time.perf_counter() - inicio
    time.sleep(0.5)
    detener.set()
    vigia.join()

    aceptadas = [cuerpo for codigo, _, cuerpo in respuestas if codigo == 202]
    sin_stock = sum(1 for codigo, _, _ in respuestas if codigo == 409)
    otros = len(respuestas) - len(aceptadas) - sin_stock
    tiempos = sorted(t * 1000 for _, t, _ in respuestas)
    print(f"  Ráfaga de 100 compras en {duracion:.2f} s")
    print(f"  {'Reserva aceptada (202)':<34}{len(aceptadas):>5}")
    print(f"  {'Rechazada: sin stock (409)':<34}{sin_stock:>5}")
    print(f"  {'Otros errores':<34}{otros:>5}")
    print(f"  Tiempo de respuesta: mediana {statistics.median(tiempos):.0f} ms | peor {tiempos[-1]:.0f} ms")
    print(f"  Mientras tanto el sistema respondió {vigilancia['ok']} de {vigilancia['ok'] + vigilancia['falla']} consultas")

    titulo("4. La Saga: el pago viaja por Kafka al servicio de pagos")
    estados = {}
    limite = time.monotonic() + 40
    for pedido in aceptadas:
        while True:
            estado = http.get(f"/pedidos/{pedido['pedido_id']}", headers=_dueno(sesiones, respuestas, pedido)).json()["estado"]
            if estado != "stock_reservado" or time.monotonic() > limite:
                break
            time.sleep(0.3)
        estados[estado] = estados.get(estado, 0) + 1
    for estado, cantidad in estados.items():
        print(f"  {estado:<20}{cantidad:>5}")

    titulo("5. ¿Cuadra el stock?")
    time.sleep(1.5)  # el proyector lleva el stock a Mongo por Kafka
    en_postgres = next(f for f in http.get("/inventario", headers=operador).json() if f["producto_id"] == producto["producto_id"])["cantidad"]
    en_mongo = next(p for p in http.get("/catalogo", headers=sesiones[0]).json() if p["producto_id"] == producto["producto_id"])["disponibles"]
    with Sesion() as sesion:
        auditoria = RepositorioInventario(sesion).saldo_movimientos(producto["producto_id"])
    print(f"  Stock en PostgreSQL (la verdad):        {en_postgres}")
    print(f"  Stock en MongoDB (lo que ve el cliente): {en_mongo}")
    print(f"  Stock según la auditoría (movimientos):  {auditoria}")

    titulo("6. Doble clic: un cliente manda 5 veces la misma compra (misma clave)")
    dejar_stock(http, operador, producto, 5)
    clave = uuid.uuid4().hex
    with ThreadPoolExecutor(max_workers=5) as ejecutor:
        repetidas = list(ejecutor.map(
            lambda _: http.post("/pedidos", json={"items": [{"producto_id": producto["producto_id"], "cantidad": 1}]},
                                headers={**sesiones[1], "Idempotency-Key": clave}),
            range(5),
        ))
    pedidos_distintos = {r.json().get("pedido_id") for r in repetidas if r.status_code == 202}
    print(f"  Respuestas: {[r.status_code for r in repetidas]}  (409 = 'ya se está procesando')")
    print(f"  Pedidos creados: {len(pedidos_distintos)}")

    titulo("RESULTADO")
    correcto = (
        len(aceptadas) == stock and otros == 0 and vigilancia["falla"] == 0
        and en_postgres == en_mongo == auditoria == 0 and len(pedidos_distintos) == 1
    )
    if correcto:
        print(f"  OK: había {stock} y se vendieron exactamente {stock}. Sin sobreventa, sin pedidos")
        print("  duplicados, el stock cuadra en las dos bases y el sistema nunca dejó de responder.")
    else:
        print("  Algo no cuadró, revisar los números de arriba.")


def _dueno(sesiones, respuestas, pedido) -> dict:
    """El pedido se consulta con la sesión de quien lo compró (cada cliente ve solo los suyos)."""
    for sesion, (_, _, cuerpo) in zip(sesiones, respuestas):
        if cuerpo.get("pedido_id") == pedido["pedido_id"]:
            return sesion
    return sesiones[0]


if __name__ == "__main__":
    main()
