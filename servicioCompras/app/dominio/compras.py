"""Reglas de la compra: la Saga orquestada (sin broker, dentro del servicio de compras).

  Paso 1. Reservar el stock (transacción local: pedido + descuento + movimiento "reserva").
  Paso 2. Autorizar el pago en la pasarela (servicio externo, con tiempo límite y Circuit Breaker).
  Paso 3. Confirmar (pedido "pagado") o compensar: devolver el stock con un movimiento
          "liberacion" y dejar el pedido "fallido".

No hay transacción distribuida: cada paso confirma su propia transacción local, y si el
paso 2 falla, el paso 1 se deshace con una acción contraria (la compensación).
El estado de la Saga queda en pedidos.estado.
"""

from sqlalchemy.orm import Session

from app.infraestructura.modelos import Pedido
from app.infraestructura.repositorios import (
    RepositorioInventario,
    RepositorioPagos,
    RepositorioPedidos,
    RepositorioProductos,
)
from app.infraestructura.servicios_externos import ClientePasarela, ServicioNoDisponible

# Límite por compra: en un evento masivo evita que un solo cliente acapare el stock.
MAXIMO_POR_COMPRA = 10


class ErrorCompra(Exception):
    """Falla prevista de la compra; el mensaje se puede mostrar al cliente."""


class ProductoNoDisponible(ErrorCompra):
    pass


class StockInsuficiente(ErrorCompra):
    pass


class PagoRechazado(ErrorCompra):
    pass


class PagoNoDisponible(ErrorCompra):
    pass


def reservar(sesion: Session, usuario_id: int, producto_id: int, cantidad: int) -> Pedido:
    """Paso 1. Quien llama confirma (commit); si se lanza una excepción, no queda nada."""
    producto = RepositorioProductos(sesion).buscar_activo(producto_id)
    if producto is None:
        raise ProductoNoDisponible("El producto no existe o no está a la venta.")

    pedido = RepositorioPedidos(sesion).crear(
        usuario_id, producto, cantidad, estado="stock_reservado"
    )
    if RepositorioInventario(sesion).reservar(producto_id, cantidad, pedido.id) is None:
        raise StockInsuficiente("No queda stock suficiente de este producto.")
    return pedido


def comprar(
    sesion: Session, pasarela: ClientePasarela, usuario_id: int, producto_id: int, cantidad: int
) -> Pedido:
    """La Saga completa. Devuelve el pedido pagado o lanza un ErrorCompra."""
    try:
        pedido = reservar(sesion, usuario_id, producto_id, cantidad)
    except ErrorCompra:
        sesion.rollback()  # no queda ni el pedido ni el descuento
        raise
    # La reserva se confirma ANTES de llamar afuera: no se mantiene abierta una
    # transacción (ni el bloqueo de la fila del stock) mientras se espera a la pasarela.
    sesion.commit()

    try:
        # Clave por pedido: si este cobro se reintenta, la pasarela no cobra dos veces.
        resultado = pasarela.autorizar(pedido.id, pedido.total, f"pedido-{pedido.id}")
    except ServicioNoDisponible as error:
        # Límite conocido: ante un tiempo límite no se sabe si la pasarela alcanzó a
        # cobrar. En producción se concilia después, consultándola con la misma clave
        # ("pedido-<id>"); aquí se compensa directamente.
        _compensar(sesion, pedido)
        raise PagoNoDisponible(
            "La pasarela de pago no responde. Tu pedido no se completó y el stock quedó "
            "libre. Inténtalo en unos minutos."
        ) from error

    RepositorioPagos(sesion).registrar(
        pedido.id,
        pedido.total,
        estado="autorizado" if resultado.autorizado else "rechazado",
        referencia=resultado.referencia,
    )
    if not resultado.autorizado:
        _compensar(sesion, pedido)
        raise PagoRechazado(f"El pago fue rechazado: {resultado.motivo} No se hizo ningún cobro.")

    pedido.estado = "pagado"
    sesion.commit()
    return pedido


def _compensar(sesion: Session, pedido: Pedido) -> None:
    """Deshace el paso 1: devuelve el stock reservado y deja el pedido fallido."""
    inventario = RepositorioInventario(sesion)
    for item in pedido.items:
        inventario.liberar(item.producto_id, item.cantidad, pedido.id)
    pedido.estado = "fallido"
    sesion.commit()
