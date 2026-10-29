"""Simulación: muchos clientes compran el mismo producto al mismo tiempo.

Usa el sistema de verdad (el backend levantado en el puerto 8000), igual que el navegador.
Muestra que se vende exactamente lo que hay, que nadie paga dos veces y que el sistema
sigue respondiendo durante la ráfaga.

Uso (con los servicios levantados), desde servicioCompras:
  python -m demostraciones.simulacion_100_usuarios            (100 clientes, stock 10)
  python -m demostraciones.simulacion_100_usuarios --stock 1  (la última unidad)
  python -m demostraciones.simulacion_100_usuarios --usuarios 50 --stock 20 --repeticiones 3
      (50 clientes que hacen triple clic: cada uno manda 3 veces la misma compra)
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
    parametros.add_argument("--usuarios", type=int, default=100, help="cuántos clientes compran (máx. 100)")
    parametros.add_argument("--stock", type=int, default=10, help="unidades del producto")
    parametros.add_argument(
        "--repeticiones", type=int, default=1,
        help="veces que cada cliente manda LA MISMA compra a la vez (doble clic = 2)",
    )
    args = parametros.parse_args()
    usuarios, stock, repeticiones = min(args.usuarios, len(CLIENTES)), args.stock, args.repeticiones
    http = httpx.Client(base_url=API, timeout=30)

    titulo("1. Revisando que la tienda esté levantada")
    revisar_servicios(http)

    titulo(f"2. Preparando: {usuarios} clientes inician sesión")
    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=20) as ejecutor:
        sesiones = list(ejecutor.map(lambda c: entrar(httpx.Client(base_url=API, timeout=30), c, CLAVE_CLIENTES), CLIENTES[:usuarios]))
    print(f"  {len(sesiones)} sesiones con JWT en {time.perf_counter() - inicio:.1f} s")
    operador = entrar(http, "operador@demo.cl", "Operador-Demo-2026")
    producto = http.get("/catalogo", headers=sesiones[0]).json()[0]
    dejar_stock(http, operador, producto, stock)
    cobros_antes = httpx.get(f"{PASARELA}/cobros").json()["total"]

    total_solicitudes = usuarios * repeticiones
    detalle = f" ({repeticiones} veces cada uno, con la misma clave)" if repeticiones > 1 else ""
    titulo(f"3. {usuarios} clientes compran '{producto['nombre']}' al mismo tiempo{detalle}")
    largada = threading.Barrier(total_solicitudes)
    vigilancia = {"ok": 0, "falla": 0, "sesion": sesiones[0]}
    detener = threading.Event()
    vigia = threading.Thread(target=vigilar, args=(detener, vigilancia))
    vigia.start()

    # Cada cliente tiene UNA clave de idempotencia; si repite el clic, repite la clave.
    claves = [uuid.uuid4().hex for _ in sesiones]
    turnos = [n for n in range(usuarios) for _ in range(repeticiones)]

    def comprar(n: int) -> tuple[int, int, float, dict]:
        with httpx.Client(base_url=API, timeout=30) as propio:
            largada.wait()  # todas las solicitudes parten en el mismo instante
            t = time.perf_counter()
            r = propio.post(
                "/pedidos",
                json={"items": [{"producto_id": producto["producto_id"], "cantidad": 1}]},
                headers={**sesiones[n], "Idempotency-Key": claves[n]},
            )
            return n, r.status_code, time.perf_counter() - t, r.json()

    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=total_solicitudes) as ejecutor:
        respuestas = list(ejecutor.map(comprar, turnos))
    duracion = time.perf_counter() - inicio
    time.sleep(0.5)
    detener.set()
    vigia.join()

    # Por cliente: qué pedidos recibió y si alguna repetición quedó frenada por "ya se está procesando".
    pedidos_de = {n: set() for n in range(usuarios)}
    en_proceso = sin_stock = otros = 0
    for n, codigo, _, cuerpo in respuestas:
        if codigo == 202:
            pedidos_de[n].add(cuerpo["pedido_id"])
        elif codigo == 409 and "procesando" in cuerpo.get("detail", ""):
            en_proceso += 1
        elif codigo == 409:
            sin_stock += 1
        else:
            otros += 1
    pedidos = {pid: n for n, ids in pedidos_de.items() for pid in ids}
    con_dos_pedidos = sum(1 for ids in pedidos_de.values() if len(ids) > 1)
    tiempos = sorted(t * 1000 for _, _, t, _ in respuestas)

    print(f"  {total_solicitudes} solicitudes en {duracion:.2f} s")
    print(f"  {'Clientes que reservaron':<44}{len(pedidos):>5}")
    print(f"  {'Clientes sin stock (409)':<44}{usuarios - len(pedidos):>5}")
    if repeticiones > 1:
        print(f"  {'Repeticiones frenadas: ya se está procesando':<44}{en_proceso:>5}")
        print(f"  {'Clientes con más de un pedido':<44}{con_dos_pedidos:>5}")
    print(f"  {'Otros errores':<44}{otros:>5}")
    print(f"  Tiempo de respuesta: mediana {statistics.median(tiempos):.0f} ms | peor {tiempos[-1]:.0f} ms")
    print(f"  Mientras tanto el sistema respondió {vigilancia['ok']} de {vigilancia['ok'] + vigilancia['falla']} consultas")

    titulo("4. La Saga: el pago viaja por Kafka al servicio de pagos")
    estados = {}
    limite = time.monotonic() + 40
    for pedido_id, n in pedidos.items():
        while True:
            estado = http.get(f"/pedidos/{pedido_id}", headers=sesiones[n]).json()["estado"]
            if estado != "stock_reservado" or time.monotonic() > limite:
                break
            time.sleep(0.3)
        estados[estado] = estados.get(estado, 0) + 1
    for estado, cantidad in estados.items():
        print(f"  {estado:<20}{cantidad:>5}")
    cobros = httpx.get(f"{PASARELA}/cobros").json()
    cobros_nuevos = cobros["total"] - cobros_antes
    claves_cobradas = [c["clave"] for c in cobros["cobros"]]
    cobros_dobles = len(claves_cobradas) - len(set(claves_cobradas))
    print(f"  Cobros nuevos en la pasarela: {cobros_nuevos} | claves cobradas dos veces: {cobros_dobles}")

    titulo("5. ¿Cuadra el stock?")
    time.sleep(1.5)  # el proyector lleva el stock a Mongo por Kafka
    en_postgres = next(f for f in http.get("/inventario", headers=operador).json() if f["producto_id"] == producto["producto_id"])["cantidad"]
    en_mongo = next(p for p in http.get("/catalogo", headers=sesiones[0]).json() if p["producto_id"] == producto["producto_id"])["disponibles"]
    with Sesion() as sesion:
        auditoria = RepositorioInventario(sesion).saldo_movimientos(producto["producto_id"])
    print(f"  Stock en PostgreSQL (la verdad):        {en_postgres}")
    print(f"  Stock en MongoDB (lo que ve el cliente): {en_mongo}")
    print(f"  Stock según la auditoría (movimientos):  {auditoria}")

    vendidas = min(stock, usuarios)
    titulo("RESULTADO")
    correcto = (
        len(pedidos) == vendidas and con_dos_pedidos == 0 and otros == 0 and vigilancia["falla"] == 0
        and estados.get("pagado", 0) == cobros_nuevos == vendidas and cobros_dobles == 0
        and en_postgres == en_mongo == auditoria == stock - vendidas
    )
    if correcto:
        print(f"  OK: había {stock} y se vendieron exactamente {vendidas}, con {vendidas} cobros.")
        if repeticiones > 1:
            print(f"  Las {total_solicitudes} solicitudes ({repeticiones} por cliente) dieron un solo pedido por cliente.")
        print("  Sin sobreventa, sin cobros dobles, el stock cuadra en las dos bases y el sistema")
        print("  nunca dejó de responder.")
    else:
        print("  Algo no cuadró, revisar los números de arriba.")


if __name__ == "__main__":
    main()
