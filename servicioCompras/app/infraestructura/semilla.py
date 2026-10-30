"""Seeder: llena Postgres y Mongo con datos de prueba coherentes entre sí.

Qué crea:
- Usuarios: uno por rol (las cuentas de demo) y clientes extra.
- Catálogo: prendas generadas por modelo y color. En Postgres va lo que importa para
  vender (nombre, precio, stock, movimientos); en Mongo el documento completo con la
  categoría y atributos que cambian según la prenda (tallas, colores, material...).
- Pedidos históricos: compras pagadas y algunas fallidas, hechas con la misma reserva
  del sistema (UPDATE condicional), así el stock sigue cuadrando con los movimientos.

Uso, desde servicioCompras:
  python -m app.infraestructura.semilla              agrega lo que falte (se puede repetir)
  python -m app.infraestructura.semilla --reiniciar  borra todo y vuelve a sembrar

LAS CLAVES DE ESTOS USUARIOS SON SOLO DE DEMO. En la BD se guardan con hash Argon2id.
"""

import random
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app.dominio import compras
from app.infraestructura.base import Sesion
from app.infraestructura.catalogo_documental import RepositorioCatalogo
from app.infraestructura.modelos import (
    Inventario,
    MovimientoInventario,
    Outbox,
    Pago,
    Pedido,
    Producto,
    Usuario,
)
from app.infraestructura.seguridad import hasheador

USUARIOS_DEMO = [
    # (correo, clave de demo, rol)
    ("cliente@demo.cl", "Cliente-Demo-2026", "cliente"),
    ("operador@demo.cl", "Operador-Demo-2026", "operador"),
    ("admin@demo.cl", "Admin-Demo-2026", "administrador"),
]
CLIENTES_EXTRA = 999  # cliente01..cliente999@demo.cl, misma clave que cliente@demo.cl (1000 clientes en total)
PEDIDOS_HISTORICOS = 60

# Atributos por categoría: cada una tiene los suyos (por eso el catálogo va en Mongo).
TALLAS_ROPA = ["XS", "S", "M", "L", "XL"]
CATEGORIAS = {
    "Polerones": {"tallas": TALLAS_ROPA, "material": "Fleece de algodón", "gramaje_g": 450},
    "Poleras": {"tallas": TALLAS_ROPA, "material": "Algodón peinado", "gramaje_g": 240},
    "Calcetines": {"tallas": ["35-38", "39-42", "43-46"], "material": "Algodón y lana merino", "pares": 3},
    "Gorras": {"tallas": ["Única"], "material": "Sarga de algodón", "ajuste": "Broche trasero"},
    "Blusas": {"tallas": TALLAS_ROPA, "material": "Lino lavado"},
    "Pantalones": {"tallas": ["38", "40", "42", "44", "46"], "material": "Sarga pesada", "tiro": "Medio"},
}

# (categoría, modelo, descripción, precio en CLP, colores)
MODELOS = [
    ("Polerones", "Polerón Oversize", "Calce holgado en fleece pesado", 44990, ["Navy", "Negro", "Crema"]),
    ("Polerones", "Polerón con Cierre", "Cierre frontal metálico oculto", 48990, ["Ice", "Gris"]),
    ("Polerones", "Polerón Crewneck", "Cuello redondo y acabados al corte", 42990, ["Heather", "Verde Oliva"]),
    ("Poleras", "Polera Básica Fit", "Calce estándar contemporáneo", 18990, ["Blanco", "Negro", "Gris"]),
    ("Poleras", "Polera Boxy Heavyweight", "Silueta cuadrada en algodón de 300 g", 26990, ["Arena", "Negro"]),
    ("Poleras", "Polera Manga Larga Raw", "Algodón mercerizado con puños sin costura", 24990, ["Blanco", "Azul"]),
    ("Calcetines", "Pack Calcetines Altos Sport", "Tres pares acanalados a media pantorrilla", 12990, ["Blanco", "Negro"]),
    ("Calcetines", "Calcetines Térmicos Waffle", "Tejido panal térmico transpirable", 14990, ["Gris", "Naranjo"]),
    ("Calcetines", "Calcetines Tobilleros Minimal", "Corte bajo invisible", 9990, ["Blanco"]),
    ("Gorras", "Gorra Dad Hat", "Gabardina de algodón lavado", 18990, ["Beige", "Negro", "Azul"]),
    ("Gorras", "Gorra Snapback Minimal", "Seis paneles con visera plana", 21990, ["Negro", "Verde"]),
    ("Gorras", "Beanie Merino", "Lana merino extrafina", 22990, ["Gris", "Burdeo"]),
    ("Blusas", "Blusa Lino Estructurada", "Corte recto en lino lavado", 36990, ["Blanco", "Celeste"]),
    ("Blusas", "Camisa Popelina Oversize", "Cuello italiano y botonadura oculta", 38990, ["Blanco", "Rayas"]),
    ("Pantalones", "Pantalón Cargo", "Corte recto con bolsillos de fuelle", 46990, ["Negro", "Verde Oliva"]),
    ("Pantalones", "Pantalón Wide Leg Chino", "Pernera ancha en twill estructurado", 44990, ["Arena", "Navy"]),
]

# Casos para la demo: uno con stock 1 (sobreventa) y uno agotado (pantalla sin stock).
STOCK_FIJO = {"Polerón Crewneck Heather": 1, "Blusa Lino Estructurada Celeste": 0}


def _catalogo() -> list[dict]:
    azar = random.Random(2026)  # siempre los mismos datos
    prendas = []
    for categoria, modelo, descripcion, precio, colores in MODELOS:
        for color in colores:
            nombre = f"{modelo} {color}"
            prendas.append(
                {
                    "nombre": nombre,
                    "descripcion": f"{descripcion}, color {color.lower()}.",
                    "categoria": categoria,
                    "precio": precio,
                    "stock": STOCK_FIJO.get(nombre, azar.choice([3, 8, 15, 20, 30, 40])),
                    "atributos": {**CATEGORIAS[categoria], "color": color},
                }
            )
    return prendas


def _crear_usuarios(sesion: Session) -> int:
    clave_cliente = USUARIOS_DEMO[0][1]
    cuentas = USUARIOS_DEMO + [
        (f"cliente{n:02d}@demo.cl", clave_cliente, "cliente") for n in range(1, CLIENTES_EXTRA + 1)
    ]
    existentes = set(sesion.scalars(select(Usuario.correo)))
    faltan = [c for c in cuentas if c[0] not in existentes]
    # Argon2 es lento a propósito (~50 ms por hash): con 1000 cuentas se hashea en paralelo.
    # Cada cuenta lleva su propio hash (sal distinta), aunque la clave de demo sea la misma.
    with ThreadPoolExecutor() as hilos:
        hashes = list(hilos.map(lambda c: hasheador.hash(c[1]), faltan))
    for (correo, _, rol), clave_hash in zip(faltan, hashes):
        sesion.add(Usuario(correo=correo, clave_hash=clave_hash, rol=rol))
    return len(faltan)


def _crear_productos(sesion: Session, prendas: list[dict]) -> int:
    creados = 0
    for prenda in prendas:
        if sesion.scalar(select(Producto.id).where(Producto.nombre == prenda["nombre"])) is not None:
            continue  # no se pisa el stock de un producto que ya existe
        producto = Producto(nombre=prenda["nombre"], descripcion=prenda["descripcion"], precio=prenda["precio"])
        sesion.add(producto)
        sesion.flush()
        sesion.add(Inventario(producto_id=producto.id, cantidad=prenda["stock"]))
        if prenda["stock"] > 0:
            # El stock inicial también queda en la auditoría: suma de movimientos = stock.
            sesion.add(
                MovimientoInventario(producto_id=producto.id, tipo="ajuste_entrada", cantidad=prenda["stock"])
            )
        creados += 1
    # Lo que no está en el catálogo (productos viejos) queda fuera de la venta, sin borrar su historia.
    nombres = [p["nombre"] for p in prendas]
    sesion.execute(update(Producto).where(Producto.nombre.not_in(nombres)).values(activo=False))
    return creados


def _crear_pedidos_historicos(sesion: Session) -> int:
    """Compras pasadas, para que el panel del administrador y "Mis pedidos" tengan datos."""
    if sesion.scalar(select(func.count()).select_from(Pedido)) > 0:
        return 0  # ya hay pedidos: no se inventan más
    azar = random.Random(29)
    clientes = list(sesion.scalars(select(Usuario.id).where(Usuario.rol == "cliente")))
    productos = list(
        sesion.scalars(select(Producto.id).join(Inventario).where(Producto.activo, Inventario.cantidad >= 6))
    )
    ahora = datetime.now(UTC)
    creados = 0
    for _ in range(PEDIDOS_HISTORICOS):
        items = {pid: azar.randint(1, 2) for pid in azar.sample(productos, azar.randint(1, 3))}
        try:
            pedido = compras.reservar(sesion, azar.choice(clientes), items)
        except compras.ErrorCompra:
            continue  # se acabó el stock de alguno: ese pedido no se crea
        pedido.creado_en = ahora - timedelta(days=azar.randint(1, 30), minutes=azar.randint(0, 1440))
        if azar.random() < 0.85:
            pedido.estado = "pagado"
            compras.avisar_pagado(sesion, pedido)
            sesion.add(Pago(pedido_id=pedido.id, monto=pedido.total, estado="autorizado", referencia_pasarela=f"AUT-SEMILLA-{pedido.id}"))
        else:
            sesion.add(Pago(pedido_id=pedido.id, monto=pedido.total, estado="rechazado"))
            compras._compensar(sesion, pedido)  # rechazado: el stock vuelve, igual que en la Saga
        creados += 1
    return creados


def _sincronizar_mongo(sesion: Session, prendas: list[dict]) -> int:
    """Copia el catálogo a Mongo con el stock actual de Postgres.

    La semilla escribe Mongo directo, así que los eventos de stock que dejó en el outbox
    se marcan como publicados (si no, el proyector los aplicaría de nuevo al arrancar).
    """
    sesion.execute(
        update(Outbox).where(Outbox.publicado_en.is_(None), Outbox.topico == "catalogo.stock").values(publicado_en=func.now())
    )
    catalogo = RepositorioCatalogo()
    catalogo.crear_indices()
    datos = {p["nombre"]: p for p in prendas}
    filas = sesion.execute(
        select(Producto, Inventario.cantidad, func.coalesce(func.max(MovimientoInventario.id), 0))
        .join(Inventario, Inventario.producto_id == Producto.id)
        .outerjoin(MovimientoInventario, MovimientoInventario.producto_id == Producto.id)
        .where(Producto.activo)
        .group_by(Producto.id, Inventario.cantidad)
    )
    sincronizados = 0
    for producto, cantidad, version in filas:
        prenda = datos.get(producto.nombre)
        if prenda is None:
            continue
        catalogo.guardar(
            producto.id,
            {
                "nombre": producto.nombre,
                "descripcion": producto.descripcion,
                "categoria": prenda["categoria"],
                "precio": producto.precio,
                "atributos": prenda["atributos"],
                "disponibles": cantidad,
                "version_stock": version,
                "activo": True,
            },
        )
        sincronizados += 1
    return sincronizados


def reiniciar() -> None:
    """Deja Postgres y Mongo vacíos (los usuarios también se borran y se vuelven a crear)."""
    with Sesion.begin() as sesion:
        sesion.execute(
            text(
                "TRUNCATE pagos, items_pedido, movimientos_inventario, claves_idempotencia, "
                "pedidos, inventario, productos, outbox, eventos_procesados, usuarios "
                "RESTART IDENTITY CASCADE"
            )
        )
    RepositorioCatalogo().borrar_todo()


def sembrar(informar: bool = False) -> tuple[int, int]:
    """Inserta lo que falte, en una sola transacción. Devuelve (usuarios, productos) creados."""
    prendas = _catalogo()
    with Sesion.begin() as sesion:
        usuarios = _crear_usuarios(sesion)
        productos = _crear_productos(sesion, prendas)
        sesion.flush()
        pedidos = _crear_pedidos_historicos(sesion)
        en_mongo = _sincronizar_mongo(sesion, prendas)
    if informar:
        print(f"Usuarios: {usuarios}. Productos: {productos}. Pedidos históricos: {pedidos}. En Mongo: {en_mongo}.")
    return usuarios, productos


if __name__ == "__main__":
    if "--reiniciar" in sys.argv:
        reiniciar()
        print("Base de datos y catálogo vacíos.")
    sembrar(informar=True)
