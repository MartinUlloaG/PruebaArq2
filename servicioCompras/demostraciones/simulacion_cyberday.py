"""Simulación de Cyberday: muchos compradores, poco stock, y cada uno se porta distinto.

Usa el sistema de verdad: la tienda (8000), la pasarela (8001), Kafka y el servicio de
pagos, por la misma API que usan el navegador y la página de pago. Cada comprador es un
hilo que hace lo mismo que una persona:

  1. inicia sesión (algunos se equivocan 3 veces y quedan bloqueados, sin JWT),
  2. aprieta Pagar al mismo tiempo que todos (gana el que reserva primero). Si la tienda
     responde 503 por mucha demanda, espera lo que dice Retry-After y reintenta con la
     MISMA clave de idempotencia, igual que la interfaz,
  3. espera la URL de la pasarela, "escribe" la tarjeta y paga o se equivoca,
  4. vuelve a la tienda con el token y espera el resultado de la Saga.
Los que se quedan sin stock recargan una vez unos segundos después: si a alguien lo
rechazaron, su unidad volvió al stock y la puede comprar otro.

Perfiles (cada cuenta tiene siempre el mismo, así un bloqueado sigue siendo el mismo):
  paga_credito     paga bien con crédito
  paga_debito      paga bien con débito (login del banco)
  se_equivoca_cvv  pone mal el CVV una vez y a la segunda lo pone bien
  sin_fondos       su tarjeta no tiene cupo: la rechazan
  cvv_3_veces      pone mal el CVV 3 veces: la tarjeta se bloquea y no compra
  banco_3_veces    pone mal la clave del banco 3 veces: se bloquea y no compra
  anula            llega a la pasarela y se arrepiente
  olvida_clave     se equivoca 3 veces en el login de la tienda: cuenta bloqueada

Uso (con todo levantado), desde servicioCompras:
  python -m demostraciones.simulacion_cyberday                       (1000 compradores, stock 100)
  python -m demostraciones.simulacion_cyberday --usuarios 200 --stock 20
  python -m demostraciones.simulacion_cyberday --repeticiones 3      (todos hacen triple clic)
"""

import argparse
import random
import statistics
import threading
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import httpx

from app.infraestructura.base import Sesion
from app.infraestructura.repositorios import RepositorioInventario

API = "http://127.0.0.1:8000"
PASARELA = "http://127.0.0.1:8001"
CLAVE_CLIENTES = "Cliente-Demo-2026"
CLIENTES = ["cliente@demo.cl"] + [f"cliente{n:02d}@demo.cl" for n in range(1, 1000)]

# (perfil, peso): de cada 100 compradores, cuántos se portan así.
PERFILES = [
    ("paga_credito", 35), ("paga_debito", 20), ("se_equivoca_cvv", 10), ("sin_fondos", 10),
    ("cvv_3_veces", 8), ("banco_3_veces", 7), ("anula", 5), ("olvida_clave", 5),
]
NO_DEBEN_PAGAR = {"sin_fondos", "cvv_3_veces", "banco_3_veces", "anula", "olvida_clave"}
DEBITO = {"paga_debito", "banco_3_veces"}

# Un cliente HTTP por servicio, compartido por todos los hilos (httpx.Client es seguro
# entre hilos). Crear 2000 clientes le roba CPU a la tienda, que corre en el mismo PC.
SIN_LIMITE = httpx.Limits(max_connections=None, max_keepalive_connections=None)
tienda = httpx.Client(base_url=API, timeout=60, limits=SIN_LIMITE)
pasarela = httpx.Client(base_url=PASARELA, timeout=60, limits=SIN_LIMITE)


def titulo(texto: str) -> None:
    print(f"\n{'=' * 78}\n {texto}\n{'=' * 78}")


def pensar(minimo: float, maximo: float) -> None:
    """Una persona se demora en leer y escribir: cada uno a su ritmo."""
    time.sleep(random.uniform(minimo, maximo))


def revisar_servicios() -> None:
    for nombre, url in [("Servicio de compras", f"{API}/salud"), ("Pasarela de pago", f"{PASARELA}/salud")]:
        try:
            httpx.get(url, timeout=3).raise_for_status()
            print(f"  [OK] {nombre}")
        except httpx.HTTPError:
            raise SystemExit(f"  [X] {nombre} no responde. Levanta la tienda primero (Levantar tienda.bat).")
    httpx.put(f"{PASARELA}/simulacion", json={"modo": "normal"})


def entrar(correo: str, clave: str) -> httpx.Response:
    return tienda.post("/autenticacion/ingresar", json={"correo": correo, "clave": clave})


def iniciar_sesion(n: int, perfil: str) -> dict:
    """Devuelve el encabezado con el JWT, o None si no se lo dieron. Guarda los códigos."""
    codigos = []
    if perfil == "olvida_clave":
        for _ in range(3):
            codigos.append(entrar(CLIENTES[n], "me-olvide-la-clave").status_code)
    r = entrar(CLIENTES[n], CLAVE_CLIENTES)  # al final pone la buena
    codigos.append(r.status_code)
    token = r.json().get("token_acceso") if r.status_code == 200 else None
    return {"codigos": codigos, "sesion": {"Authorization": f"Bearer {token}"} if token else None}


def pedir_compra(cuerpo: dict, encabezados: dict, resultado: dict) -> httpx.Response:
    """Como la interfaz: con 503 (mucha demanda) espera y reintenta con la MISMA clave."""
    for _ in range(60):
        r = tienda.post("/pedidos", json=cuerpo, headers=encabezados)
        if r.status_code != 503:
            return r
        resultado["esperas"] += 1
        time.sleep(float(r.headers.get("Retry-After", 2)) + random.uniform(0, 1))
    return r


def esperar(sesion: dict, pedido_id: int, listo, segundos: float = 90) -> dict:
    """Consulta el pedido cada ~1 s (como la interfaz) hasta que `listo(pedido)`."""
    limite = time.monotonic() + segundos
    while True:
        pedido = tienda.get(f"/pedidos/{pedido_id}", headers=sesion).json()
        if listo(pedido) or time.monotonic() > limite:
            return pedido
        time.sleep(random.uniform(0.8, 1.2))


def en_la_pasarela(token: str, perfil: str, tarjeta: dict, repeticiones: int) -> str:
    """Lo que hace el comprador en la página de pago. Devuelve cómo quedó la transacción."""
    base = f"/transacciones/{token}"
    credito = {"tipo": "credito", "numero": tarjeta["numero"], "vencimiento": tarjeta["vencimiento"], "cvv": tarjeta["cvv"]}
    cvv_malo = {**credito, "cvv": f"{(int(tarjeta['cvv']) + 1) % 1000:03d}"}

    def enviar(ruta: str, datos: dict) -> dict:
        return pasarela.post(base + ruta, json=datos).json()

    def con_doble_clic(ruta: str, datos: dict) -> dict:
        # Con --repeticiones el comprador también aprieta "Pagar" varias veces seguidas.
        with ThreadPoolExecutor(max_workers=repeticiones) as clics:
            return list(clics.map(lambda _: enviar(ruta, datos), range(repeticiones)))[-1]

    pensar(1, 4)  # escribe la tarjeta
    if perfil == "anula":
        return enviar("/anular", {})["estado"]
    if perfil in DEBITO:
        enviar("/tarjeta", {"tipo": "debito", "numero": tarjeta["numero"]})
        pensar(1, 3)  # login del banco
        rut = tarjeta["rut"]
        if perfil == "banco_3_veces":
            for _ in range(3):
                vista = enviar("/banco", {"rut": rut, "clave": "0000" if tarjeta["clave_banco"] != "0000" else "1111"})
                pensar(0.5, 1.5)
            return vista["estado"]
        return con_doble_clic("/banco", {"rut": rut, "clave": tarjeta["clave_banco"]})["estado"]
    if perfil == "cvv_3_veces":
        for _ in range(3):
            vista = enviar("/tarjeta", cvv_malo)
            pensar(0.5, 1.5)
        return vista["estado"]
    if perfil == "se_equivoca_cvv":
        enviar("/tarjeta", cvv_malo)
        pensar(0.5, 1.5)
    return con_doble_clic("/tarjeta", credito)["estado"]


def comprar(n: int, perfil: str, sesion: dict, tarjeta: dict, producto_id: int, largada: threading.Barrier,
            repeticiones: int) -> dict:
    resultado = {"perfil": perfil, "reservas": 0, "sin_stock": 0, "esperas": 0, "pedidos": set(), "final": None}
    largada.wait(timeout=300)  # todos aprietan Pagar en el mismo instante
    for vuelta in range(2):  # si no alcanzó, recarga una vez
        clave = uuid.uuid4().hex  # una clave por compra; el doble clic repite la misma
        cuerpo = {"items": [{"producto_id": producto_id, "cantidad": 1}]}
        encabezados = {**sesion, "Idempotency-Key": clave}
        t = time.perf_counter()
        with ThreadPoolExecutor(max_workers=repeticiones) as clics:
            respuestas = list(clics.map(lambda _: pedir_compra(cuerpo, encabezados, resultado), range(repeticiones)))
        resultado.setdefault("ms_reserva", (time.perf_counter() - t) * 1000)
        aceptadas = [r.json() for r in respuestas if r.status_code == 202]
        if aceptadas:
            break
        if any(r.status_code == 409 and "stock" in r.json()["detail"] for r in respuestas):
            resultado["sin_stock"] += 1
        if vuelta == 0:
            pensar(3, 8)  # "se acabó... recargo a ver si se liberó alguna"
    else:
        return resultado

    resultado["pedidos"] = {p["pedido_id"] for p in aceptadas}
    pedido_id = aceptadas[0]["pedido_id"]
    resultado["reservas"] = 1
    pedido = esperar(sesion, pedido_id, lambda p: p["pago"]["url_pago"] or p["estado"] != "stock_reservado")
    if not pedido["pago"]["url_pago"]:
        resultado["final"] = pedido["estado"]
        return resultado
    token = pedido["pago"]["url_pago"].rsplit("/", 1)[1]

    en_la_pasarela(token, perfil, tarjeta, repeticiones)
    # Vuelve a la tienda (y con --repeticiones recarga la página de vuelta varias veces).
    for _ in range(repeticiones):
        tienda.post("/pedidos/confirmar-pago", json={"token": token}, headers=sesion)
    pedido = esperar(sesion, pedido_id, lambda p: p["estado"] != "stock_reservado")
    resultado["final"] = pedido["estado"]
    return resultado


def vigilar(detener: threading.Event, contador: Counter, sesion: dict) -> None:
    """Mientras dura el Cyberday, otro "usuario" navega el catálogo: ¿el sistema responde?"""
    with httpx.Client(base_url=API, timeout=5) as http:
        while not detener.is_set():
            for ruta in ("/salud", "/catalogo/categorias"):
                try:
                    contador["ok" if http.get(ruta, headers=sesion).status_code == 200 else "falla"] += 1
                except httpx.HTTPError:
                    contador["falla"] += 1
            time.sleep(0.1)


def main() -> None:
    parametros = argparse.ArgumentParser()
    parametros.add_argument("--usuarios", type=int, default=1000, help="cuántos compradores (máx. 1000)")
    parametros.add_argument("--stock", type=int, default=100, help="unidades del producto")
    parametros.add_argument("--repeticiones", type=int, default=1, help="clics por botón (doble clic = 2)")
    args = parametros.parse_args()
    usuarios, stock, repeticiones = min(args.usuarios, len(CLIENTES)), args.stock, max(1, args.repeticiones)

    titulo("1. Revisando que la tienda esté levantada")
    revisar_servicios()

    # Mismo perfil para la misma cuenta en cada corrida (semilla fija).
    azar = random.Random(2026)
    nombres, pesos = zip(*PERFILES)
    perfiles = azar.choices(nombres, weights=pesos, k=len(CLIENTES))[:usuarios]

    titulo(f"2. Antes del Cyberday: el banco emite {usuarios} tarjetas y todos inician sesión")
    pedidos_tarjeta = [{"tipo": "debito" if p in DEBITO else "credito", "saldo": 0 if p == "sin_fondos" else 5_000_000} for p in perfiles]
    tarjetas = pasarela.post("/simulacion/tarjetas", json=pedidos_tarjeta).json()
    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=100) as hilos:
        logins = list(hilos.map(lambda n: iniciar_sesion(n, perfiles[n]), range(usuarios)))
    con_sesion = [n for n in range(usuarios) if logins[n]["sesion"]]
    olvidadizos = [n for n in range(usuarios) if perfiles[n] == "olvida_clave"]
    print(f"  {len(con_sesion)} sesiones con JWT en {time.perf_counter() - inicio:.1f} s")
    ejemplo = next((logins[n]["codigos"] for n in olvidadizos), None)
    if ejemplo:
        print(f"  {len(olvidadizos)} se equivocaron 3 veces. Respuestas de uno (3 malas + la buena): {ejemplo}")
        print("  401 = clave mala, 423 = cuenta bloqueada: ni con la clave buena recibe JWT.")

    operador = {"Authorization": f"Bearer {entrar('operador@demo.cl', 'Operador-Demo-2026').json()['token_acceso']}"}
    sesion_vigia = logins[con_sesion[0]]["sesion"]
    producto = tienda.get("/catalogo", headers=sesion_vigia).json()[0]
    fila = next(f for f in tienda.get("/inventario", headers=operador).json() if f["producto_id"] == producto["producto_id"])
    if diferencia := stock - fila["cantidad"]:
        tipo = "ajuste_entrada" if diferencia > 0 else "ajuste_salida"
        tienda.patch(f"/inventario/{producto['producto_id']}", json={"cantidad": abs(diferencia), "tipo": tipo}, headers=operador).raise_for_status()
    print(f"  El operador dejó '{producto['nombre']}' con {stock} unidades a {producto['precio']:,} CLP.".replace(",", "."))
    cobros_antes = httpx.get(f"{PASARELA}/cobros").json()["total"]

    titulo(f"3. Cyberday: {len(con_sesion)} compradores aprietan Pagar al mismo tiempo")
    largada = threading.Barrier(len(con_sesion))
    vigilancia = Counter()
    detener = threading.Event()
    vigia = threading.Thread(target=vigilar, args=(detener, vigilancia, sesion_vigia))
    vigia.start()
    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=len(con_sesion)) as hilos:
        resultados = list(hilos.map(
            lambda n: comprar(n, perfiles[n], logins[n]["sesion"], tarjetas[n], producto["producto_id"], largada, repeticiones),
            con_sesion,
        ))
    duracion = time.perf_counter() - inicio
    detener.set()
    vigia.join()
    print(f"  Todo el evento duró {duracion:.1f} s (incluye el tiempo que cada uno se demora en escribir la tarjeta)")
    tiempos = sorted(r["ms_reserva"] for r in resultados if "ms_reserva" in r)
    print(f"  Respuesta al apretar Pagar: mediana {statistics.median(tiempos):.0f} ms | peor {tiempos[-1]:.0f} ms")
    print(f"  Mientras tanto el catálogo respondió {vigilancia['ok']} de {vigilancia['ok'] + vigilancia['falla']} consultas")
    esperas = sum(r["esperas"] for r in resultados)
    con_espera = sum(1 for r in resultados if r["esperas"])
    print(f"  Load shedding: {con_espera} compradores recibieron 503 ({esperas} veces) y reintentaron con su misma clave")

    titulo("4. Qué le pasó a cada tipo de comprador")
    por_perfil = {nombre: Counter() for nombre in nombres}
    for n in range(usuarios):
        por_perfil[perfiles[n]]["total"] += 1
        if not logins[n]["sesion"]:
            por_perfil[perfiles[n]]["sin_jwt"] += 1
    for r in resultados:
        c = por_perfil[r["perfil"]]
        c["reservaron"] += r["reservas"]
        c["sin_stock"] += 1 if not r["reservas"] else 0
        c["pagaron"] += r["final"] == "pagado"
        c["rechazados"] += r["final"] == "fallido"
    print(f"  {'Perfil':<17}{'Total':>6}{'Sin JWT':>9}{'Sin stock':>11}{'Reservó':>9}{'Pagó':>7}{'Rechazado':>11}")
    for nombre in nombres:
        c = por_perfil[nombre]
        print(f"  {nombre:<17}{c['total']:>6}{c['sin_jwt']:>9}{c['sin_stock']:>11}{c['reservaron']:>9}{c['pagaron']:>7}{c['rechazados']:>11}")
    pagados = sum(c["pagaron"] for c in por_perfil.values())
    reservaron = sum(c["reservaron"] for c in por_perfil.values())
    segunda_vuelta = sum(1 for r in resultados if r["reservas"] and r["sin_stock"])
    print(f"\n  Reservaron {reservaron} y pagaron {pagados}. {reservaron - pagados} unidades volvieron al stock por rechazos.")
    print(f"  {segunda_vuelta} compradores se quedaron sin stock, recargaron y alcanzaron una unidad que liberó otro.")

    titulo("5. ¿Cuadra todo?")
    time.sleep(2)  # el proyector lleva el stock a Mongo por Kafka
    cobros = httpx.get(f"{PASARELA}/cobros").json()
    cobros_nuevos = cobros["total"] - cobros_antes
    claves = [c["clave"] for c in cobros["cobros"]]
    cobros_dobles = len(claves) - len(set(claves))
    con_dos_pedidos = sum(1 for r in resultados if len(r["pedidos"]) > 1)
    colgados = sum(1 for r in resultados if r["reservas"] and r["final"] not in ("pagado", "fallido"))
    pagaron_sin_deber = sum(por_perfil[p]["pagaron"] for p in NO_DEBEN_PAGAR)
    olvidadizos_con_jwt = sum(1 for n in olvidadizos if logins[n]["sesion"])
    en_postgres = next(f for f in tienda.get("/inventario", headers=operador).json() if f["producto_id"] == producto["producto_id"])["cantidad"]
    en_mongo = next(p for p in tienda.get("/catalogo", headers=sesion_vigia).json() if p["producto_id"] == producto["producto_id"])["disponibles"]
    with Sesion() as sesion:
        auditoria = RepositorioInventario(sesion).saldo_movimientos(producto["producto_id"])

    revisiones = [
        (f"Sin sobreventa: se pagaron {pagados} de {stock}", pagados <= stock),
        (f"Cobros en la pasarela = pedidos pagados ({cobros_nuevos} = {pagados})", cobros_nuevos == pagados),
        (f"Ninguna clave cobrada dos veces ({cobros_dobles})", cobros_dobles == 0),
        (f"Nadie con dos pedidos por la misma compra ({con_dos_pedidos})", con_dos_pedidos == 0),
        (f"Nadie que debía fallar terminó pagando ({pagaron_sin_deber})", pagaron_sin_deber == 0),
        (f"Ningún bloqueado recibió JWT ({olvidadizos_con_jwt})", olvidadizos_con_jwt == 0),
        (f"Ninguna reserva quedó colgada ({colgados})", colgados == 0),
        (f"Stock: Postgres {en_postgres} = Mongo {en_mongo} = auditoría {auditoria} = {stock} - {pagados}",
         en_postgres == en_mongo == auditoria == stock - pagados),
        (f"El sistema nunca dejó de responder ({vigilancia['falla']} fallas)", vigilancia["falla"] == 0),
    ]
    for texto, ok in revisiones:
        print(f"  [{'OK' if ok else 'X '}] {texto}")

    titulo("RESULTADO")
    if all(ok for _, ok in revisiones):
        print(f"  OK: {usuarios} compradores por {stock} unidades. Cada rechazo devolvió su unidad al stock,")
        print("  nadie pagó dos veces, ningún bloqueado compró y el stock cuadra en las dos bases.")
    else:
        print("  Algo no cuadró, revisar las líneas con [X].")


if __name__ == "__main__":
    main()
