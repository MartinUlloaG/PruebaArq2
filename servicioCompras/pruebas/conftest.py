import uuid

import pytest
from sqlalchemy import delete, select

from ayudantes import PRECIO
from app.infraestructura import mensajeria
from app.infraestructura.base import Sesion
from app.infraestructura.modelos import (
    Inventario,
    ItemPedido,
    MovimientoInventario,
    Outbox,
    Pago,
    Pedido,
    Producto,
)
from app.infraestructura.semilla import sembrar


@pytest.fixture(scope="session", autouse=True)
def datos_demo():
    sembrar()


@pytest.fixture
def crear_producto():
    """Fábrica: crea un producto con stock (y su movimiento de entrada) y lo borra al final,
    con sus pedidos, pagos y mensajes del outbox. Así no se gasta el stock de la demo."""
    creados = []

    def crear(stock: int) -> int:
        with Sesion.begin() as sesion:
            producto = Producto(nombre=f"Prueba {uuid.uuid4().hex[:8]}", precio=PRECIO)
            sesion.add(producto)
            sesion.flush()
            sesion.add(Inventario(producto_id=producto.id, cantidad=stock))
            sesion.add(
                MovimientoInventario(producto_id=producto.id, tipo="ajuste_entrada", cantidad=stock)
            )
        creados.append(producto.id)
        return producto.id

    yield crear

    with Sesion.begin() as sesion:
        for producto_id in creados:
            pedidos = select(ItemPedido.pedido_id).where(ItemPedido.producto_id == producto_id)
            pedido_ids = list(sesion.scalars(pedidos))
            sesion.execute(
                delete(Outbox).where(
                    (Outbox.topico != mensajeria.CAMBIOS_STOCK) & Outbox.clave.in_([str(i) for i in pedido_ids])
                    | (Outbox.topico == mensajeria.CAMBIOS_STOCK) & (Outbox.clave == str(producto_id))
                )
            )
            sesion.execute(delete(MovimientoInventario).where(MovimientoInventario.producto_id == producto_id))
            sesion.execute(delete(ItemPedido).where(ItemPedido.pedido_id.in_(pedido_ids)))
            sesion.execute(delete(Pago).where(Pago.pedido_id.in_(pedido_ids)))
            sesion.execute(delete(Pedido).where(Pedido.id.in_(pedido_ids)))
            sesion.execute(delete(Inventario).where(Inventario.producto_id == producto_id))
            sesion.execute(delete(Producto).where(Producto.id == producto_id))
