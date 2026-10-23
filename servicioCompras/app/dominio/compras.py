"""Reglas de la compra. Hoy implementa el paso 1 de la Saga: reservar el stock.

Todo ocurre dentro de la transacción de la sesión recibida. Quien llama confirma
(commit); si aquí se lanza una excepción, la sesión se cierra sin confirmar y no
queda nada guardado: ni pedido, ni descuento de stock, ni movimiento.
"""

from sqlalchemy.orm import Session

from app.infraestructura.modelos import Pedido
from app.infraestructura.repositorios import (
    RepositorioInventario,
    RepositorioPedidos,
    RepositorioProductos,
)

# Límite por compra: en un evento masivo evita que un solo cliente acapare el stock.
MAXIMO_POR_COMPRA = 10


class ErrorCompra(Exception):
    """Falla prevista de la compra; el mensaje se puede mostrar al cliente."""


class ProductoNoDisponible(ErrorCompra):
    pass


class StockInsuficiente(ErrorCompra):
    pass


def reservar(sesion: Session, usuario_id: int, producto_id: int, cantidad: int) -> Pedido:
    producto = RepositorioProductos(sesion).buscar_activo(producto_id)
    if producto is None:
        raise ProductoNoDisponible("El producto no existe o no está a la venta.")

    pedido = RepositorioPedidos(sesion).crear(
        usuario_id, producto, cantidad, estado="stock_reservado"
    )
    if RepositorioInventario(sesion).reservar(producto_id, cantidad, pedido.id) is None:
        raise StockInsuficiente("No queda stock suficiente de este producto.")
    return pedido
