"""Reglas de la compra: la Saga orquestada sobre Kafka.

  Paso 1. Reservar el stock y dejar en el outbox la solicitud "autorizar pago",
          en UNA transacción (pedido + descuento + movimiento + mensaje).
  Paso 2. El servicio de pagos lee la solicitud, cobra en la pasarela y publica el
          resultado en pagos.resultados (eso pasa en otro proceso: servicioPagos).
  Paso 3. Al llegar el resultado: pedido "pagado", o compensar devolviendo el stock
          (movimiento "liberacion") y dejar el pedido "fallido".

Reserva con TTL: si el resultado no llega a tiempo (servicio de pagos caído, pasarela
caída, mensaje en la DLQ), la reserva vence y también se compensa. El stock nunca queda
tomado para siempre.

No hay transacción distribuida: cada paso confirma su propia transacción local. El
estado de la Saga queda en pedidos.estado.
"""

from sqlalchemy.orm import Session

from app.infraestructura import mensajeria
from app.infraestructura.modelos import Pedido
from app.infraestructura.repositorios import (
    RepositorioEventos,
    RepositorioInventario,
    RepositorioOutbox,
    RepositorioPagos,
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


def reservar(sesion: Session, usuario_id: int, items: dict[int, int]) -> Pedido:
    """Reserva el stock de todo el carrito ({producto_id: cantidad}) en una transacción.

    O se reservan todos los productos o ninguno: si uno no alcanza, se lanza la excepción
    y quien llama hace rollback. Quien llama confirma (commit).
    Se reserva en orden de producto_id: si dos carritos comparten productos, los dos
    bloquean las filas en el mismo orden y no se pueden trabar entre ellos (deadlock).
    """
    productos = RepositorioProductos(sesion)
    lineas = []
    for producto_id in sorted(items):
        producto = productos.buscar_activo(producto_id)
        if producto is None:
            raise ProductoNoDisponible("Un producto del carrito no existe o ya no está a la venta.")
        lineas.append((producto, items[producto_id]))

    pedido = RepositorioPedidos(sesion).crear(usuario_id, lineas, estado="stock_reservado")
    inventario = RepositorioInventario(sesion)
    for producto, cantidad in lineas:
        if inventario.reservar(producto.id, cantidad, pedido.id) is None:
            raise StockInsuficiente(f"No queda stock suficiente de {producto.nombre}.")
    return pedido


def iniciar_compra(sesion: Session, usuario_id: int, items: dict[int, int]) -> Pedido:
    """Paso 1 de la Saga. Devuelve el pedido con el stock reservado y el pago en camino."""
    try:
        pedido = reservar(sesion, usuario_id, items)
    except ErrorCompra:
        sesion.rollback()  # no queda ni el pedido ni el descuento
        raise
    RepositorioOutbox(sesion).agregar(
        mensajeria.SOLICITUDES_PAGO,
        clave=str(pedido.id),
        contenido={
            "id_evento": f"solicitud-pedido-{pedido.id}",
            "pedido_id": pedido.id,
            "monto": pedido.total,
            # La pasarela no cobra dos veces la misma clave, aunque la solicitud se reintente.
            "clave_idempotencia": f"pedido-{pedido.id}",
        },
    )
    sesion.commit()
    return pedido


def aplicar_resultado_pago(sesion: Session, evento: dict) -> None:
    """Paso 3 de la Saga. Consumidor idempotente: un evento repetido no hace nada."""
    if not RepositorioEventos(sesion).registrar(evento["id_evento"]):
        sesion.rollback()
        return

    pedido = RepositorioPedidos(sesion).buscar_para_actualizar(evento["pedido_id"])
    if pedido is None or pedido.estado != "stock_reservado":
        # Llegó tarde: la reserva ya venció y el stock se devolvió. Si igual se cobró,
        # no se puede arreglar solo: va a la DLQ para revisarlo a mano (y reembolsar).
        if evento["autorizado"]:
            RepositorioOutbox(sesion).agregar(
                mensajeria.MUERTOS,
                clave=str(evento["pedido_id"]),
                contenido={"motivo": "Cobro autorizado de un pedido que ya no estaba vigente.", "evento": evento},
            )
        sesion.commit()
        return

    RepositorioPagos(sesion).registrar(
        pedido.id,
        pedido.total,
        estado="autorizado" if evento["autorizado"] else "rechazado",
        referencia=evento.get("referencia"),
    )
    if evento["autorizado"]:
        pedido.estado = "pagado"
    else:
        _compensar(sesion, pedido)
    sesion.commit()


def expirar_reservas(sesion: Session, segundos: int) -> int:
    """TTL de la reserva: compensa los pedidos que esperan el pago hace demasiado."""
    vencidos = RepositorioPedidos(sesion).reservas_vencidas(segundos)
    for pedido in vencidos:
        _compensar(sesion, pedido)
    sesion.commit()
    return len(vencidos)


def _compensar(sesion: Session, pedido: Pedido) -> None:
    """Deshace el paso 1: devuelve el stock reservado y deja el pedido fallido."""
    inventario = RepositorioInventario(sesion)
    for item in pedido.items:
        inventario.liberar(item.producto_id, item.cantidad, pedido.id)
    pedido.estado = "fallido"
