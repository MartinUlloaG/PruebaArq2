import time
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.configuracion import configuracion
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


class PagoNoEncontrado(ErrorCompra):
    pass


def reservar(sesion: Session, usuario_id: int, items: dict[int, int]) -> Pedido:
    """Reserva el stock de todo el carrito ({producto_id: cantidad}) en una transacción.

    O se reservan todos los productos o ninguno: si uno no alcanza, se lanza la excepción
    y quien llama hace rollback. Quien llama confirma (commit).
    Se reserva en orden de producto_id: si dos carritos comparten productos, los dos
    bloquean las filas en el mismo orden y no se pueden trabar entre ellos (deadlock).
    """
    productos = RepositorioProductos(sesion)
    inventario = RepositorioInventario(sesion)
    lineas = []
    for producto_id in sorted(items):
        producto = productos.buscar_activo(producto_id)
        if producto is None:
            raise ProductoNoDisponible("Un producto del carrito no existe o ya no está a la venta.")
        # Si ya se agotó, se responde al tiro: no hace falta hacer fila por la fila bloqueada.
        if inventario.disponibles(producto_id) < items[producto_id]:
            raise StockInsuficiente(f"No queda stock suficiente de {producto.nombre}.")
        lineas.append((producto, items[producto_id]))

    pedido = RepositorioPedidos(sesion).crear(usuario_id, lineas, estado="stock_reservado")
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
    RepositorioPagos(sesion).registrar(pedido.id, pedido.total, estado="pendiente")
    RepositorioOutbox(sesion).agregar(
        mensajeria.SOLICITUDES_PAGO,
        clave=str(pedido.id),  
        contenido={
            "id_evento": f"solicitud-pedido-{pedido.id}",
            "tipo": "iniciar",
            "pedido_id": pedido.id,
            "monto": pedido.total,
            "clave_idempotencia": f"pedido-{pedido.id}",
            "url_retorno": configuracion.url_retorno_pago,
            "pagar_antes_de": time.time() + configuracion.segundos_reserva - configuracion.segundos_margen_confirmacion,
        },
    )
    sesion.commit()
    return pedido


def pedir_confirmacion(sesion: Session, usuario_id: int, token: str) -> Pedido:
    """Paso 3: el comprador volvió de la pasarela con su token.

    Se puede llamar varias veces (recargó la página, doble pestaña): el pedido se bloquea
    (FOR UPDATE) y la solicitud "confirmar" se deja una sola vez.
    """
    pedido_id = RepositorioPagos(sesion).pedido_del_token(token, usuario_id)
    if pedido_id is None:
        raise PagoNoEncontrado("No encontramos ese pago.")
    pedido = RepositorioPedidos(sesion).buscar_para_actualizar(pedido_id)
    pago = pedido.pago
    if pedido.estado == "stock_reservado" and pago.confirmacion_pedida_en is None:
        pago.confirmacion_pedida_en = datetime.now(UTC)
        RepositorioOutbox(sesion).agregar(
            mensajeria.SOLICITUDES_PAGO,
            clave=str(pedido.id),
            contenido={
                "id_evento": f"confirmacion-pedido-{pedido.id}",
                "tipo": "confirmar",
                "pedido_id": pedido.id,
                "token": token,
                "clave_idempotencia": f"pedido-{pedido.id}",
            },
        )
    sesion.commit()
    return pedido


def aplicar_resultado_pago(sesion: Session, evento: dict) -> None:
    """Lo que publica el servicio de pagos (pasos 2 y 4). Consumidor idempotente: un
    evento repetido no hace nada."""
    if not RepositorioEventos(sesion).registrar(evento["id_evento"]):
        sesion.rollback()
        return
    if evento.get("tipo") == "transaccion_creada":
        _guardar_transaccion(sesion, evento)
    else:
        _aplicar_resultado(sesion, evento)
    sesion.commit()


def _guardar_transaccion(sesion: Session, evento: dict) -> None:
    """Paso 2: guarda el token y la URL donde paga el comprador."""
    pedido = RepositorioPedidos(sesion).buscar_para_actualizar(evento["pedido_id"])
    if pedido is None or pedido.estado != "stock_reservado":
        return  # la reserva ya venció: nadie va a confirmar, y la pasarela no cobra sin confirmar
    pago = pedido.pago or RepositorioPagos(sesion).registrar(pedido.id, pedido.total, estado="pendiente")
    pago.token_pasarela = evento["token"]
    pago.url_pago = evento["url_pago"]


def _aplicar_resultado(sesion: Session, evento: dict) -> None:
    """Paso 4: pagado o compensar."""
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
        return

    pago = pedido.pago or RepositorioPagos(sesion).registrar(pedido.id, pedido.total, estado="pendiente")
    pago.estado = "autorizado" if evento["autorizado"] else "rechazado"
    pago.referencia_pasarela = evento.get("referencia")
    pago.medio = evento.get("medio")
    pago.motivo = evento.get("motivo")
    if evento["autorizado"]:
        pedido.estado = "pagado"
        avisar_pagado(sesion, pedido)
    else:
        _compensar(sesion, pedido)


def avisar_pagado(sesion: Session, pedido: Pedido) -> None:
    """Evento pedidos.pagados (por el outbox): lo consume el servicio de recomendaciones."""
    RepositorioOutbox(sesion).agregar(
        mensajeria.PEDIDOS_PAGADOS,
        clave=str(pedido.id),
        contenido={
            # Único por evento: si el relay lo publica dos veces, el consumidor lo reconoce.
            "id_evento": f"pagado-{uuid.uuid4().hex}",
            "pedido_id": pedido.id,
            "items": [{"producto_id": i.producto_id, "cantidad": i.cantidad} for i in pedido.items],
        },
    )


def expirar_reservas(sesion: Session, segundos: int) -> int:
    """TTL de la reserva: compensa los pedidos que esperan el pago hace demasiado."""
    vencidos = RepositorioPedidos(sesion).reservas_vencidas(segundos)
    for pedido in vencidos:
        _compensar(sesion, pedido)
        if pedido.pago and pedido.pago.estado == "pendiente":
            pedido.pago.estado = "rechazado"
            pedido.pago.motivo = "La reserva venció sin que se completara el pago."
    sesion.commit()
    return len(vencidos)


def _compensar(sesion: Session, pedido: Pedido) -> None:
    """Deshace el paso 1: devuelve el stock reservado y deja el pedido fallido."""
    inventario = RepositorioInventario(sesion)
    for item in pedido.items:
        inventario.liberar(item.producto_id, item.cantidad, pedido.id)
    pedido.estado = "fallido"
