"""Prueba de carga visual: 100.000 compradores contra el sistema levantado.

Lo que se ve en vivo en la consola:
- La avalancha: cuántos llegaron, cuántos hay comprando a la vez y compras por segundo.
- La tienda: reservas, sin stock (409), frenados por load shedding (503, reintentan con
  la misma clave) y el doble clic frenado por la idempotencia.
- Los pagos de los que alcanzaron stock: en la pasarela, pagados y rechazados.
- La resiliencia: a los pocos segundos se bota la pasarela un rato. Se ve el Circuit
  Breaker del servicio de pagos abrirse y cerrarse (estado real, leído de :8002/estado),
  las pocas llamadas que le llegan a la pasarela caída y lo que va a la DLQ.
- Al final revisa: sin sobreventa, cobros = pedidos pagados, ninguna clave cobrada dos
  veces, ningún doble clic con dos pedidos, 0 errores, el stock cuadra en Postgres, Mongo
  y la auditoría, y el sistema nunca dejó de responder.

Los 100 mil no llegan en el mismo milisegundo (un solo PC no puede): llegan como una
avalancha, con --en-vuelo compradores a la vez y el resto haciendo fila, como en un
Cyberday. Usa las 1000 cuentas de la semilla (cada cuenta la comparten 100 compradores,
cada uno con su propia compra y su propia clave de idempotencia).

Uso (con todo levantado), desde servicioCompras:
  python -m demostraciones.simulacion_100k
  python -m demostraciones.simulacion_100k --compradores 20000 --stock 300
  python -m demostraciones.simulacion_100k --sin-caida
"""

import argparse
import asyncio
import json
import random
import statistics
import time
import uuid
from collections import Counter, deque

import aiohttp
from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text
from sqlalchemy import func, select

from app.infraestructura.base import Sesion
from app.infraestructura.modelos import ItemPedido, Pedido
from app.infraestructura.repositorios import RepositorioInventario

API = "http://127.0.0.1:8000"
PASARELA = "http://127.0.0.1:8001"
PAGOS = "http://127.0.0.1:8002"
CLAVE_CLIENTES = "Cliente-Demo-2026"
CUENTAS = ["cliente@demo.cl"] + [f"cliente{n:02d}@demo.cl" for n in range(1, 1000)]

# Qué hace en la pasarela el que alcanza stock (de cada 100).
PERFILES = [
    ("paga_credito", 45), ("paga_debito", 20), ("se_equivoca_cvv", 10), ("sin_fondos", 10),
    ("cvv_3_veces", 7), ("banco_3_veces", 4), ("anula", 4),
]
NO_DEBEN_PAGAR = {"sin_fondos", "cvv_3_veces", "banco_3_veces", "anula"}
DEBITO = {"paga_debito", "banco_3_veces"}
DOBLE_CLIC = 0.10  # 1 de cada 10 aprieta Pagar 2 o 3 veces seguidas
SEGUNDA_VUELTA = 0.05  # de los que quedan sin stock, cuántos recargan a ver si se liberó algo

COLOR_CIRCUITO = {"cerrado": "bold green", "abierto": "bold red", "semiabierto": "bold yellow"}


# ------------------------------------------------------------------ cliente HTTP
# aiohttp y no httpx: un solo proceso de Python tiene que generar cientos de compras por
# segundo, y con httpx la prueba misma era el cuello de botella (~100 por segundo).


class ErrorHttp(Exception):
    pass


ErrorRed = (aiohttp.ClientError, asyncio.TimeoutError, ErrorHttp)


class Respuesta:
    def __init__(self, codigo: int, encabezados, texto: str):
        self.status_code, self.headers, self.text = codigo, encabezados, texto

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise ErrorHttp(f"HTTP {self.status_code}")


class Cliente:
    """Lo mínimo de httpx que usa la prueba, encima de una sesión de aiohttp."""

    def __init__(self, sesion: aiohttp.ClientSession, base: str):
        self.sesion, self.base = sesion, base

    async def _pedir(self, metodo: str, ruta: str, json=None, headers=None, timeout: float | None = None) -> Respuesta:
        url = ruta if ruta.startswith("http") else self.base + ruta
        extra = {"timeout": aiohttp.ClientTimeout(total=timeout)} if timeout else {}
        async with self.sesion.request(metodo, url, json=json, headers=headers, **extra) as r:
            return Respuesta(r.status, r.headers, await r.text())

    async def get(self, ruta, **kw):
        return await self._pedir("GET", ruta, **kw)

    async def post(self, ruta, **kw):
        return await self._pedir("POST", ruta, **kw)

    async def put(self, ruta, **kw):
        return await self._pedir("PUT", ruta, **kw)

    async def patch(self, ruta, **kw):
        return await self._pedir("PATCH", ruta, **kw)


class Estado:
    """Todo lo que muestra la consola. Lo escriben los compradores y lo lee el dibujo."""

    def __init__(self, total: int, stock: int):
        self.total, self.stock_inicial = total, stock
        self.fase, self.detalle_fase = "Preparando", ""
        self.inicio = None
        self.llegaron = self.en_vuelo = self.terminados = 0
        self.tienda = Counter()
        self.pagos = Counter()
        self.por_perfil = {nombre: Counter() for nombre, _ in PERFILES}
        self.dobles: dict[str, set] = {}  # clave -> pedidos creados (debe ser 1 o 0)
        self.marcas = deque()  # cuándo terminó cada compra, para las compras por segundo
        self.stock_pg = self.stock_mongo = None
        self.pasarela = {"modo": "normal", "recibidas": 0, "rechazadas": 0}
        self.base_pasarela = None
        self.servicio_pagos = {"circuito": "?", "aperturas": 0, "a_la_dlq": 0, "reintentos": 0}
        self.base_pagos = None
        self.circuitos_vistos = set()
        self.caida = {"activa": False, "rechazadas": 0, "esperando": 0}
        self.recomendaciones = "?"
        self.latencias = deque(maxlen=300)
        self.vigia_ok = self.vigia_fallas = 0
        self.procesos_nucleo = set()
        self.eventos = deque(maxlen=7)
        self.revisiones = None

    def evento(self, texto: str) -> None:
        segundos = int(time.monotonic() - self.inicio) if self.inicio else 0
        self.eventos.append(f"{segundos // 60:02d}:{segundos % 60:02d}  {texto}")

    def por_segundo(self) -> int:
        ahora = time.monotonic()
        while self.marcas and ahora - self.marcas[0] > 5:
            self.marcas.popleft()
        return round(len(self.marcas) / 5)

    def delta(self, fuente: dict, base: dict | None, clave: str) -> int:
        return fuente.get(clave, 0) - (base or {}).get(clave, 0)


# ------------------------------------------------------------------ el dibujo


def _panel(titulo: str, filas: list[tuple], color: str) -> Panel:
    tabla = Table.grid(padding=(0, 2), expand=True)
    tabla.add_column(ratio=3)
    tabla.add_column(justify="right", ratio=1)
    for nombre, valor, *estilo in filas:
        tabla.add_row(nombre, Text(f"{valor:,}".replace(",", ".") if isinstance(valor, int) else str(valor),
                                   style=estilo[0] if estilo else ""))
    return Panel(tabla, title=f"[bold]{titulo}", border_style=color)


def dibujar(e: Estado) -> Group:
    pasado = time.monotonic() - e.inicio if e.inicio else 0
    titulo = Text.assemble(
        ("  CYBERDAY KYRO · ", "bold white on #293241"),
        (f"{e.total:,} COMPRADORES ".replace(",", "."), "bold white on #ee6c4d"),
        (f"  {e.fase}", "bold"),
        (f"  {e.detalle_fase}", "dim"),
        (f"   {int(pasado) // 60:02d}:{int(pasado) % 60:02d}", "bold cyan"),
    )

    avance = Table.grid(expand=True)
    avance.add_column(ratio=4)
    avance.add_column(justify="right", ratio=2)
    avance.add_row(ProgressBar(total=e.total, completed=e.terminados, width=None),
                   f"{e.terminados:,} de {e.total:,} terminaron".replace(",", "."))
    avance.add_row(Text(f"Comprando ahora: {e.en_vuelo:,}   ·   {e.por_segundo():,} compras por segundo".replace(",", "."),
                        style="cyan"), "")

    t = e.tienda
    tienda = _panel("Tienda: apretar Pagar", [
        ("Reservaron una unidad (202)", t["reservaron"], "bold green"),
        ("Sin stock (409)", t["sin_stock"]),
        ("Frenados por load shedding (503)", t["frenados_503"], "yellow"),
        ("  └ reintentaron con su misma clave", t["reintentos_503"], "yellow"),
        ("Doble clic frenado (idempotencia)", t["doble_clic"], "magenta"),
        ("Recargaron y alcanzaron (2ª vuelta)", t["segunda_vuelta_ok"], "green"),
        ("Conexión cortada, reintentó con su clave", t["reintentos_red"], "dim"),
        ("Errores", t["errores"], "bold red" if t["errores"] else "green"),
    ], "#3d5a80")

    p = e.pagos
    pagos = _panel("Pagos en la pasarela", [
        ("Esperando la URL de pago", p["esperando_url"]),
        ("Pagando en la pasarela", p["en_pasarela"]),
        ("Pagados", p["pagados"], "bold green"),
        ("Rechazados (cupo, CVV, banco, anuló)", p["rechazados"], "yellow"),
        ("Sin pasarela (DLQ, venció la reserva)", p["sin_pasarela"], "red" if p["sin_pasarela"] else ""),
    ], "#3d5a80")

    vendidas = e.stock_inicial - e.stock_pg if e.stock_pg is not None else 0
    stock = _panel("Stock del producto", [
        ("Stock inicial", e.stock_inicial),
        ("Disponible en Postgres (la verdad)", e.stock_pg if e.stock_pg is not None else "…", "bold"),
        ("Disponible en Mongo (lo que ve el cliente)", e.stock_mongo if e.stock_mongo is not None else "…"),
        ("Reservado o vendido", max(vendidas, 0)),
    ], "#3d5a80")

    circuito = e.servicio_pagos.get("circuito", "?")
    modo = e.pasarela.get("modo", "?")
    latencias = sorted(e.latencias)
    p50 = f"{statistics.median(latencias):.0f} ms" if latencias else "…"
    p95 = f"{latencias[int(len(latencias) * 0.95) - 1]:.0f} ms" if len(latencias) > 20 else "…"
    resiliencia = _panel("Resiliencia", [
        ("Pasarela de pago", "CAÍDA" if modo == "falla" else modo.upper(), "bold red" if modo == "falla" else "bold green"),
        ("Circuit Breaker hacia la pasarela", circuito.upper(), COLOR_CIRCUITO.get(circuito, "")),
        ("  └ veces que se abrió", e.delta(e.servicio_pagos, e.base_pagos, "aperturas")),
        ("Llamadas que llegaron a la pasarela caída", e.delta(e.pasarela, e.base_pasarela, "rechazadas"), "yellow"),
        ("Reintentos del servicio de pagos", e.delta(e.servicio_pagos, e.base_pagos, "reintentos")),
        ("Mensajes a la DLQ", e.delta(e.servicio_pagos, e.base_pagos, "a_la_dlq"), "red"),
        ("Circuito de recomendaciones", e.recomendaciones.upper(), COLOR_CIRCUITO.get(e.recomendaciones, "")),
    ], "#ee6c4d")

    sistema = _panel("¿Responde el sistema? (otro usuario navegando)", [
        ("Réplicas del núcleo atendiendo", len(e.procesos_nucleo - {None}), "bold cyan"),
        ("Consultas respondidas", e.vigia_ok, "green"),
        ("Consultas fallidas", e.vigia_fallas, "bold red" if e.vigia_fallas else "green"),
        ("Tiempo de respuesta (mediana)", p50),
        ("Tiempo de respuesta (95%)", p95),
    ], "#ee6c4d")

    fila1 = Table.grid(expand=True, padding=(0, 1))
    for _ in range(3):
        fila1.add_column(ratio=1)
    fila1.add_row(tienda, pagos, stock)
    fila2 = Table.grid(expand=True, padding=(0, 1))
    fila2.add_column(ratio=3)
    fila2.add_column(ratio=2)
    fila2.add_row(resiliencia, sistema)

    eventos = Panel(Text("\n".join(e.eventos) or "…", style="white"), title="[bold]Qué va pasando", border_style="dim")
    partes = [titulo, Panel(avance, border_style="cyan"), fila1, fila2, eventos]

    if e.revisiones is not None:
        tabla = Table(show_header=False, box=None, expand=True)
        tabla.add_column(width=6)
        tabla.add_column()
        for texto, ok in e.revisiones:
            tabla.add_row(Text(" OK " if ok else " X  ", style="bold black on green" if ok else "bold white on red"), texto)
        todo_ok = all(ok for _, ok in e.revisiones)
        partes.append(Panel(tabla, title="[bold]¿Cuadra todo?",
                            border_style="green" if todo_ok else "red",
                            subtitle="[bold green]RESULTADO: OK" if todo_ok else "[bold red]RESULTADO: algo no cuadró"))
    return Group(*partes)


# ------------------------------------------------------------------ los compradores


async def pedir_compra(e: Estado, http: Cliente, cuerpo: dict, encabezados: dict) -> Respuesta | None:
    """Como la interfaz: con 503 (load shedding) espera y reintenta con la MISMA clave.
    Si se corta la conexión también reintenta con la misma clave: para eso está la
    idempotencia. Solo cuenta como error si después de 3 cortes sigue sin respuesta."""
    cortes = 0
    for intento in range(60):
        try:
            r = await http.post("/pedidos", json=cuerpo, headers=encabezados)
        except ErrorRed:
            cortes += 1
            if cortes == 3:
                e.tienda["errores"] += 1
                return None
            e.tienda["reintentos_red"] += 1
            await asyncio.sleep(random.uniform(0.5, 1.5))
            continue
        if r.status_code != 503:
            return r
        e.tienda["frenados_503"] += 1
        if intento:
            e.tienda["reintentos_503"] += 1
        await asyncio.sleep(float(r.headers.get("Retry-After", 2)) + random.uniform(0, 1.5))
    return r


async def esperar(http, sesion, pedido_id, listo, hasta: float) -> dict | None:
    """Consulta el pedido cada ~2 s (como la interfaz) hasta que `listo(pedido)`."""
    pedido = None
    while time.monotonic() < hasta:
        try:
            pedido = (await http.get(f"/pedidos/{pedido_id}", headers=sesion)).json()
            if listo(pedido):
                return pedido
        except (*ErrorRed, ValueError):
            pass
        await asyncio.sleep(random.uniform(1.5, 2.5))
    return pedido


async def en_la_pasarela(pasarela: Cliente, token: str, perfil: str, tarjeta: dict) -> None:
    """Lo que hace el comprador en la página de pago, según su perfil."""
    base = f"/transacciones/{token}"
    credito = {"tipo": "credito", "numero": tarjeta["numero"], "vencimiento": tarjeta["vencimiento"], "cvv": tarjeta["cvv"]}
    cvv_malo = {**credito, "cvv": f"{(int(tarjeta['cvv']) + 1) % 1000:03d}"}
    await asyncio.sleep(random.uniform(1, 3))  # escribe la tarjeta
    if perfil == "anula":
        await pasarela.post(base + "/anular", json={})
    elif perfil in DEBITO:
        await pasarela.post(base + "/tarjeta", json={"tipo": "debito", "numero": tarjeta["numero"]})
        await asyncio.sleep(random.uniform(0.5, 1.5))
        clave = tarjeta["clave_banco"] if perfil == "paga_debito" else ("0000" if tarjeta["clave_banco"] != "0000" else "1111")
        for _ in range(1 if perfil == "paga_debito" else 3):
            await pasarela.post(base + "/banco", json={"rut": tarjeta["rut"], "clave": clave})
    elif perfil == "cvv_3_veces":
        for _ in range(3):
            await pasarela.post(base + "/tarjeta", json=cvv_malo)
    else:
        if perfil == "se_equivoca_cvv":
            await pasarela.post(base + "/tarjeta", json=cvv_malo)
            await asyncio.sleep(random.uniform(0.5, 1.5))
        await pasarela.post(base + "/tarjeta", json=credito)


async def pagar(e: Estado, http, pasarela, sesion: dict, pedido_id: int, ttl: int) -> None:
    perfil = random.choices([n for n, _ in PERFILES], weights=[w for _, w in PERFILES])[0]
    hasta = time.monotonic() + ttl + 90
    e.pagos["esperando_url"] += 1
    pedido = await esperar(http, sesion, pedido_id,
                           lambda p: p["pago"] and (p["pago"]["url_pago"] or p["estado"] != "stock_reservado"), hasta)
    e.pagos["esperando_url"] -= 1

    if pedido and pedido["pago"] and pedido["pago"]["url_pago"]:
        token = pedido["pago"]["url_pago"].rsplit("/", 1)[1]
        e.pagos["en_pasarela"] += 1
        try:
            saldo = 0 if perfil == "sin_fondos" else 5_000_000
            tarjeta = (await pasarela.post("/simulacion/tarjetas", json=[
                {"tipo": "debito" if perfil in DEBITO else "credito", "saldo": saldo}])).json()[0]
            await en_la_pasarela(pasarela, token, perfil, tarjeta)
            await http.post("/pedidos/confirmar-pago", json={"token": token}, headers=sesion)  # volvió a la tienda
        except ErrorRed:
            pass  # se cortó; si no confirmó, la reserva vence sola
        e.pagos["en_pasarela"] -= 1
        sin_pasarela = False
    else:
        sin_pasarela = True  # la transacción nunca se creó (pasarela caída, DLQ): la reserva vence sola

    pedido = await esperar(http, sesion, pedido_id, lambda p: p["estado"] != "stock_reservado", hasta)
    estado = pedido["estado"] if pedido else "?"
    e.por_perfil[perfil][estado] += 1
    if estado == "pagado":
        e.pagos["pagados"] += 1
    elif sin_pasarela:
        e.pagos["sin_pasarela"] += 1
    else:
        e.pagos["rechazados"] += 1


async def comprador(e: Estado, http, pasarela, sesion: dict, producto_id: int, pagos: set, ttl: int,
                    segunda: bool = False) -> None:
    clave = uuid.uuid4().hex  # su "número de ticket"; el doble clic repite el mismo
    clics = random.choice([2, 3]) if random.random() < DOBLE_CLIC else 1
    cuerpo = {"items": [{"producto_id": producto_id, "cantidad": 1}]}
    encabezados = {**sesion, "Idempotency-Key": clave}
    respuestas = await asyncio.gather(*(pedir_compra(e, http, cuerpo, encabezados) for _ in range(clics)))
    e.marcas.append(time.monotonic())

    ids, sin_stock = set(), False
    for r in respuestas:
        if r is None:
            continue
        if r.status_code == 202:
            ids.add(r.json()["pedido_id"])
        elif r.status_code == 409 and "procesando" in r.text:
            e.tienda["doble_clic"] += 1  # el mismo ticket mientras el primero sigue en curso
        elif r.status_code == 409:
            sin_stock = True
        elif r.status_code >= 500 or r.status_code in (401, 403, 422):
            e.tienda["errores"] += 1
    if clics > 1:
        e.dobles[clave] = ids
        e.tienda["doble_clic"] += sum(1 for r in respuestas if r is not None and r.status_code == 202) - len(ids)

    if ids:
        e.tienda["segunda_vuelta_ok" if segunda else "reservaron"] += 1
        tarea = asyncio.create_task(pagar(e, http, pasarela, sesion, next(iter(ids)), ttl))
        pagos.add(tarea)
        tarea.add_done_callback(pagos.discard)
    elif sin_stock and not segunda:
        e.tienda["sin_stock"] += 1
        if random.random() < SEGUNDA_VUELTA:  # "se acabó... recargo a ver si alguien liberó una"
            async def recargar():
                await asyncio.sleep(random.uniform(4, 15))
                await comprador(e, http, pasarela, sesion, producto_id, pagos, ttl, segunda=True)
            tarea = asyncio.create_task(recargar())
            pagos.add(tarea)
            tarea.add_done_callback(pagos.discard)


# ------------------------------------------------------------------ lo que corre al lado


async def vigilar(e: Estado, http: Cliente, sesion: dict, operador: dict, producto_id: int, detener: asyncio.Event):
    """Otro usuario navegando, más el estado de la pasarela, del servicio de pagos y del stock."""
    vuelta = 0
    while not detener.is_set():
        inicio = time.perf_counter()
        try:
            salud = (await http.get("/salud", timeout=15)).json()
            r = await http.get("/catalogo/categorias", headers=sesion, timeout=15)
            r.raise_for_status()
            e.latencias.append((time.perf_counter() - inicio) * 1000 / 2)
            e.vigia_ok += 1
            e.recomendaciones = salud.get("circuito_recomendaciones", "?")
            e.procesos_nucleo.add(salud.get("proceso"))
        except (*ErrorRed, ValueError):
            e.vigia_fallas += 1
        try:
            e.pasarela = (await http.get(f"{PASARELA}/simulacion", timeout=5)).json()
            antes = e.servicio_pagos.get("circuito")
            e.servicio_pagos = (await http.get(f"{PAGOS}/estado", timeout=5)).json()
            ahora = e.servicio_pagos["circuito"]
            e.circuitos_vistos.add(ahora)
            if antes not in (None, "?", ahora):
                e.evento(f"Circuit Breaker del servicio de pagos: {antes.upper()} → {ahora.upper()}")
        except (*ErrorRed, ValueError):
            pass
        if vuelta % 3 == 0:
            try:
                fila = next(f for f in (await http.get("/inventario", headers=operador)).json() if f["producto_id"] == producto_id)
                if e.stock_pg and fila["cantidad"] == 0:
                    e.evento("Se agotó el stock en Postgres: desde ahora se responde 409 al tiro")
                e.stock_pg = fila["cantidad"]
                catalogo = (await http.get("/catalogo", headers=sesion)).json()
                e.stock_mongo = next(p["disponibles"] for p in catalogo if p["producto_id"] == producto_id)
            except (*ErrorRed, ValueError, StopIteration):
                pass
        vuelta += 1
        await asyncio.sleep(0.5)


async def botar_pasarela(e: Estado, http: Cliente, en: float, dura: float) -> None:
    """Caos a propósito: la pasarela se cae un rato en pleno Cyberday."""
    await asyncio.sleep(en)
    antes = (await http.put(f"{PASARELA}/simulacion", json={"modo": "falla"})).json()
    e.caida["esperando"] = e.pagos["esperando_url"] + e.pagos["en_pasarela"]
    e.evento(f"CAOS: se cae la pasarela de pago por {dura:.0f} s ({e.caida['esperando']} pagos en curso)")
    await asyncio.sleep(dura)
    await http.put(f"{PASARELA}/simulacion", json={"modo": "normal"})
    despues = (await http.get(f"{PASARELA}/simulacion")).json()
    e.caida["rechazadas"] = despues["rechazadas"] - antes.get("rechazadas", 0)
    e.evento("La pasarela volvió. El circuito deja pasar una llamada de prueba y se cierra solo")


def reservas_colgadas(producto_id: int) -> int:
    with Sesion() as sesion:
        return sesion.scalar(
            select(func.count(func.distinct(Pedido.id)))
            .join(ItemPedido, ItemPedido.pedido_id == Pedido.id)
            .where(ItemPedido.producto_id == producto_id, Pedido.estado == "stock_reservado")
        )


# ------------------------------------------------------------------ la prueba


async def correr(e: Estado, args, live: Live) -> None:
    # keepalive 3 s: uvicorn cierra las conexiones inactivas a los 5 s; si el cliente las
    # reusa después de eso sale "Server disconnected" sin que el servidor haya fallado.
    conector = aiohttp.TCPConnector(limit=args.en_vuelo + 300, limit_per_host=0, keepalive_timeout=3)
    async with aiohttp.ClientSession(connector=conector, timeout=aiohttp.ClientTimeout(total=120)) as sesion_http:
        http, pasarela = Cliente(sesion_http, API), Cliente(sesion_http, PASARELA)
        # 1. ¿Está todo arriba?
        e.fase = "Revisando servicios"
        for nombre, url in [("Servicio de compras", f"{API}/salud"), ("Pasarela", f"{PASARELA}/salud"),
                            ("Servicio de pagos", f"{PAGOS}/estado")]:
            try:
                (await http.get(url, timeout=5)).raise_for_status()
                e.evento(f"{nombre}: arriba")
            except ErrorRed:
                e.evento(f"{nombre} NO responde. Levanta la tienda (y reinicia el servicio de pagos si es antiguo).")
                e.fase = "Detenido"
                return
        await http.put(f"{PASARELA}/simulacion", json={"modo": "normal"})
        ttl = (await http.get("/salud")).json().get("segundos_reserva", 420)

        # 2. Antes del Cyberday: todos inician sesión
        e.fase = "Iniciando sesión"
        cupos = asyncio.Semaphore(50)
        listas = []

        async def entrar(correo: str):
            async with cupos:
                try:
                    r = await http.post("/autenticacion/ingresar", timeout=60,
                                        json={"correo": correo, "clave": CLAVE_CLIENTES})
                except ErrorRed:
                    return  # esa cuenta queda fuera; las demás siguen
                if r.status_code == 200:
                    listas.append({"Authorization": f"Bearer {r.json()['token_acceso']}"})
                e.detalle_fase = f"{len(listas)} de {len(CUENTAS)} cuentas"

        await asyncio.gather(*(entrar(c) for c in CUENTAS))
        e.evento(f"{len(listas)} cuentas con sesión (JWT); cada una la comparten ~{e.total // max(len(listas), 1)} compradores")
        r = await http.post("/autenticacion/ingresar", json={"correo": "operador@demo.cl", "clave": "Operador-Demo-2026"})
        operador = {"Authorization": f"Bearer {r.json()['token_acceso']}"}

        # 3. El operador deja el stock
        e.fase = "Preparando stock"
        producto = (await http.get("/catalogo", headers=listas[0])).json()[0]
        pid = producto["producto_id"]
        fila = next(f for f in (await http.get("/inventario", headers=operador)).json() if f["producto_id"] == pid)
        stock_original = fila["cantidad"]
        if diferencia := e.stock_inicial - stock_original:
            await http.patch(f"/inventario/{pid}", headers=operador, json={
                "cantidad": abs(diferencia), "tipo": "ajuste_entrada" if diferencia > 0 else "ajuste_salida"})
        e.stock_pg = e.stock_mongo = e.stock_inicial
        e.evento(f"'{producto['nombre']}' con {e.stock_inicial} unidades. Reserva de {ttl} s.")
        cobros_antes = (await http.get(f"{PASARELA}/cobros")).json()["total"]
        e.base_pasarela = dict((await http.get(f"{PASARELA}/simulacion")).json())
        e.base_pagos = dict((await http.get(f"{PAGOS}/estado")).json())

        # 4. La avalancha
        e.fase, e.detalle_fase = "CYBERDAY", ""
        e.inicio = time.monotonic()
        e.evento(f"¡Empieza! {e.total:,} compradores, {args.en_vuelo} a la vez".replace(",", "."))
        detener = asyncio.Event()
        vigia = asyncio.create_task(vigilar(e, http, listas[0], operador, pid, detener))
        caos = None if args.sin_caida else asyncio.create_task(botar_pasarela(e, http, args.caida_en, args.caida))

        pagos: set = set()
        cupos = asyncio.Semaphore(args.en_vuelo)
        compras: set = set()

        async def uno(n: int):
            try:
                await comprador(e, http, pasarela, listas[n % len(listas)], pid, pagos, ttl)
            finally:
                e.en_vuelo -= 1
                e.terminados += 1
                cupos.release()

        for n in range(e.total):
            await cupos.acquire()
            e.llegaron += 1
            e.en_vuelo += 1
            tarea = asyncio.create_task(uno(n))
            compras.add(tarea)
            tarea.add_done_callback(compras.discard)
        await asyncio.gather(*compras)
        e.evento(f"Llegaron los {e.total:,} compradores. Terminando los pagos en curso".replace(",", "."))

        # 5. Terminan los pagos (y las segundas vueltas)
        e.fase = "Terminando pagos"
        if caos:
            await caos
        while pagos:
            e.detalle_fase = f"{len(pagos)} en curso"
            await asyncio.sleep(1)
            await asyncio.gather(*list(pagos), return_exceptions=True)

        # 6. Reservas que quedaron sin pagar (por la DLQ): vencen solas
        e.fase = "Esperando que venzan las reservas sin pago"
        hasta = time.monotonic() + ttl + 60
        while (colgadas := await asyncio.to_thread(reservas_colgadas, pid)) and time.monotonic() < hasta:
            e.detalle_fase = f"{colgadas} reservas, vencen en ≤ {int(hasta - time.monotonic()) - 60} s"
            await asyncio.sleep(2)

        # 7. ¿Cuadra todo?
        e.fase, e.detalle_fase = "Revisando", ""
        await asyncio.sleep(3)  # el proyector lleva los últimos cambios a Mongo
        detener.set()
        await vigia
        en_pg = next(f for f in (await http.get("/inventario", headers=operador)).json() if f["producto_id"] == pid)["cantidad"]
        en_mongo = next(p for p in (await http.get("/catalogo", headers=listas[0])).json() if p["producto_id"] == pid)["disponibles"]
        with Sesion() as sesion:
            auditoria = RepositorioInventario(sesion).saldo_movimientos(pid)
        cobros = (await http.get(f"{PASARELA}/cobros")).json()
        claves = [c["clave"] for c in cobros["cobros"]]
        pagados = e.pagos["pagados"]
        cobros_nuevos = cobros["total"] - cobros_antes
        dobles_con_dos = sum(1 for ids in e.dobles.values() if len(ids) > 1)
        pagaron_sin_deber = sum(e.por_perfil[p]["pagado"] for p in NO_DEBEN_PAGAR)
        colgadas = await asyncio.to_thread(reservas_colgadas, pid)
        e.stock_pg, e.stock_mongo = en_pg, en_mongo

        e.revisiones = [
            (f"Sin sobreventa: se pagaron {pagados} de {e.stock_inicial} unidades", pagados <= e.stock_inicial),
            (f"Cobros en la pasarela = pedidos pagados ({cobros_nuevos} = {pagados})", cobros_nuevos == pagados),
            (f"Ninguna clave cobrada dos veces ({len(claves) - len(set(claves))})", len(claves) == len(set(claves))),
            (f"Doble clic: {len(e.dobles):,} compradores apretaron 2-3 veces y ninguno quedó con dos pedidos ({dobles_con_dos})".replace(",", "."),
             dobles_con_dos == 0),
            (f"Nadie que debía fallar terminó pagando ({pagaron_sin_deber})", pagaron_sin_deber == 0),
            (f"Errores en las compras ({e.tienda['errores']})", e.tienda["errores"] == 0),
            (f"Ninguna reserva quedó colgada ({colgadas})", colgadas == 0),
            (f"Stock: Postgres {en_pg} = Mongo {en_mongo} = auditoría {auditoria} = {e.stock_inicial} - {pagados}",
             en_pg == en_mongo == auditoria == e.stock_inicial - pagados),
            (f"El sistema nunca dejó de responder ({e.vigia_ok:,} consultas, {e.vigia_fallas} fallas)".replace(",", "."),
             e.vigia_fallas == 0),
        ]
        if not args.sin_caida:
            abrio = e.delta(e.servicio_pagos, e.base_pagos, "aperturas")
            e.revisiones.append((
                f"Con la pasarela caída el circuito se abrió ({abrio} vez/veces), le llegaron solo "
                f"{e.caida['rechazadas']} llamadas y volvió a cerrarse ({e.servicio_pagos.get('circuito')})",
                abrio >= 1 and e.servicio_pagos.get("circuito") == "cerrado",
            ))

        # El producto vuelve a su stock de antes, para no dejar la demo cambiada.
        if diferencia := stock_original - en_pg:
            await http.patch(f"/inventario/{pid}", headers=operador, json={
                "cantidad": abs(diferencia), "tipo": "ajuste_entrada" if diferencia > 0 else "ajuste_salida"})
        e.fase = "Terminado"
        e.evento(f"Listo. El producto volvió a su stock original ({stock_original}).")


async def principal(args) -> None:
    e = Estado(args.compradores, args.stock)
    with Live(dibujar(e), refresh_per_second=4, screen=False) as live:
        async def refrescar():
            while True:
                live.update(dibujar(e))
                await asyncio.sleep(0.25)

        dibujo = asyncio.create_task(refrescar())
        try:
            await correr(e, args, live)
        finally:
            dibujo.cancel()
            try:  # pase lo que pase, la pasarela queda funcionando
                async with aiohttp.ClientSession() as sesion_http:
                    await Cliente(sesion_http, PASARELA).put("/simulacion", json={"modo": "normal"}, timeout=5)
            except ErrorRed:
                pass
            live.update(dibujar(e))


def main() -> None:
    parametros = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parametros.add_argument("--compradores", type=int, default=100_000)
    parametros.add_argument("--stock", type=int, default=300, help="unidades del producto")
    parametros.add_argument("--en-vuelo", type=int, default=800, help="compradores comprando a la vez")
    parametros.add_argument("--caida-en", type=float, default=6, help="segundos hasta que se cae la pasarela")
    parametros.add_argument("--caida", type=float, default=12, help="segundos que dura caída")
    parametros.add_argument("--sin-caida", action="store_true", help="no botar la pasarela")
    asyncio.run(principal(parametros.parse_args()))


if __name__ == "__main__":
    main()
