"""Compra: reserva de stock, idempotencia y los pasos de la Saga en el servicio de compras.

Pruebas de cierre: stock 1 y 100 compras simultáneas, exactamente 1 éxito; la misma
clave de idempotencia dos veces deja una sola reserva y un solo mensaje de pago; si el
pago se rechaza o la reserva vence, el stock vuelve.

Estas pruebas no necesitan Kafka: revisan lo que la compra deja en el outbox y llaman
directo a los pasos que ejecutan los consumidores. La prueba con Kafka de verdad está
en test_saga_kafka.py.
"""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update

from ayudantes import (
    PRECIO,
    cliente_http,
    comprar,
    encabezado,
    estado_pedido_y_pago,
    mensajes_outbox,
    pedidos_del_producto,
    stock_y_saldo,
)
from app.dominio import compras
from app.infraestructura import mensajeria
from app.infraestructura.base import Sesion
from app.infraestructura.modelos import Pedido, Usuario


def _resultado(pedido_id: int, autorizado: bool) -> dict:
    """El evento que publicaría el servicio de pagos."""
    return {
        "id_evento": f"resultado-pedido-{pedido_id}",
        "pedido_id": pedido_id,
        "autorizado": autorizado,
        "referencia": "AUT-prueba" if autorizado else None,
        "motivo": None if autorizado else "Fondos insuficientes.",
    }


def _aplicar(evento: dict) -> None:
    with Sesion() as sesion:
        compras.aplicar_resultado_pago(sesion, evento)


# --- Paso 1: reservar y dejar el pago en camino -------------------------------


def test_comprar_reserva_el_stock_y_deja_la_solicitud_de_pago(crear_producto):
    producto_id = crear_producto(stock=3)
    respuesta = comprar(producto_id, 2)
    pedido = respuesta.json()

    assert respuesta.status_code == 202  # aceptado: el pago se resuelve después
    assert pedido["estado"] == "stock_reservado"
    assert pedido["total"] == 2 * PRECIO
    assert stock_y_saldo(producto_id) == (1, 1)  # stock y auditoría cuadran
    # Outbox: la solicitud quedó en la misma transacción que la reserva.
    [solicitud] = mensajes_outbox(pedido["pedido_id"], mensajeria.SOLICITUDES_PAGO)
    assert solicitud["monto"] == 2 * PRECIO
    assert solicitud["clave_idempotencia"] == f"pedido-{pedido['pedido_id']}"


def test_el_cliente_consulta_su_pedido(crear_producto):
    producto_id = crear_producto(stock=1)
    creado = comprar(producto_id, 1).json()
    respuesta = cliente_http.get(f"/pedidos/{creado['pedido_id']}", headers=encabezado("cliente"))
    mis_pedidos = cliente_http.get("/pedidos", headers=encabezado("cliente")).json()
    assert respuesta.json()["estado"] == "stock_reservado"
    assert creado["pedido_id"] in [p["pedido_id"] for p in mis_pedidos]


def test_pedido_que_no_existe_responde_404():
    respuesta = cliente_http.get("/pedidos/999999", headers=encabezado("cliente"))
    assert respuesta.status_code == 404


# --- Idempotencia --------------------------------------------------------------


def test_la_misma_clave_dos_veces_deja_una_sola_compra(crear_producto):
    producto_id = crear_producto(stock=5)
    clave = uuid.uuid4().hex
    primera = comprar(producto_id, 1, clave=clave)
    segunda = comprar(producto_id, 1, clave=clave)  # doble clic o reintento de red

    assert primera.status_code == segunda.status_code == 202
    assert primera.json() == segunda.json()  # misma respuesta, mismo pedido
    assert stock_y_saldo(producto_id) == (4, 4)  # se reservó una sola vez
    assert pedidos_del_producto(producto_id) == 1
    assert len(mensajes_outbox(primera.json()["pedido_id"], mensajeria.SOLICITUDES_PAGO)) == 1


def test_la_misma_clave_con_otra_compra_responde_422(crear_producto):
    producto_id = crear_producto(stock=5)
    clave = uuid.uuid4().hex
    assert comprar(producto_id, 1, clave=clave).status_code == 202
    assert comprar(producto_id, 2, clave=clave).status_code == 422
    assert stock_y_saldo(producto_id) == (4, 4)


def test_sin_clave_de_idempotencia_responde_422(crear_producto):
    producto_id = crear_producto(stock=1)
    respuesta = cliente_http.post(
        "/pedidos", json={"items": [{"producto_id": producto_id, "cantidad": 1}]}, headers=encabezado("cliente")
    )
    assert respuesta.status_code == 422
    assert stock_y_saldo(producto_id) == (1, 1)


# --- Paso 3: aplicar el resultado del pago --------------------------------------


def test_pago_autorizado_deja_el_pedido_pagado(crear_producto):
    producto_id = crear_producto(stock=3)
    pedido_id = comprar(producto_id, 2).json()["pedido_id"]

    _aplicar(_resultado(pedido_id, autorizado=True))

    assert estado_pedido_y_pago(pedido_id) == ("pagado", "autorizado")
    assert stock_y_saldo(producto_id) == (1, 1)


def test_pago_rechazado_compensa_y_devuelve_el_stock(crear_producto):
    producto_id = crear_producto(stock=3)
    pedido_id = comprar(producto_id, 2).json()["pedido_id"]

    _aplicar(_resultado(pedido_id, autorizado=False))

    assert estado_pedido_y_pago(pedido_id) == ("fallido", "rechazado")
    assert stock_y_saldo(producto_id) == (3, 3)  # reserva (-2) + liberacion (+2)


def test_un_resultado_repetido_no_se_aplica_dos_veces(crear_producto):
    """Consumidor idempotente: Kafka puede entregar el mismo evento dos veces."""
    producto_id = crear_producto(stock=3)
    pedido_id = comprar(producto_id, 2).json()["pedido_id"]

    _aplicar(_resultado(pedido_id, autorizado=False))
    _aplicar(_resultado(pedido_id, autorizado=False))

    assert stock_y_saldo(producto_id) == (3, 3)  # se devolvió una sola vez, no 4 de más


# --- TTL de la reserva -----------------------------------------------------------


def _envejecer(pedido_id: int, segundos: int) -> None:
    with Sesion.begin() as sesion:
        hace = datetime.now(UTC) - timedelta(seconds=segundos)
        sesion.execute(update(Pedido).where(Pedido.id == pedido_id).values(creado_en=hace))


def test_la_reserva_vence_si_el_pago_no_llega(crear_producto):
    producto_id = crear_producto(stock=3)
    pedido_id = comprar(producto_id, 1).json()["pedido_id"]
    _envejecer(pedido_id, segundos=120)

    with Sesion() as sesion:
        compras.expirar_reservas(sesion, segundos=60)

    assert estado_pedido_y_pago(pedido_id) == ("fallido", "rechazado")  # el pago queda con su motivo
    assert stock_y_saldo(producto_id) == (3, 3)


def test_un_cobro_que_llega_tarde_va_a_la_dlq(crear_producto):
    """Si la reserva ya venció y después llega "autorizado", se cobró sin producto:
    no se puede arreglar solo, así que queda en la DLQ para revisarlo a mano."""
    producto_id = crear_producto(stock=3)
    pedido_id = comprar(producto_id, 1).json()["pedido_id"]
    _envejecer(pedido_id, segundos=120)
    with Sesion() as sesion:
        compras.expirar_reservas(sesion, segundos=60)

    _aplicar(_resultado(pedido_id, autorizado=True))

    assert estado_pedido_y_pago(pedido_id) == ("fallido", "rechazado")  # el pago queda con su motivo  # no revive el pedido
    assert stock_y_saldo(producto_id) == (3, 3)
    [muerto] = mensajes_outbox(pedido_id, mensajeria.MUERTOS)
    assert muerto["evento"]["pedido_id"] == pedido_id


# --- Reglas y validaciones --------------------------------------------------


def test_sin_stock_suficiente_responde_409_y_no_guarda_nada(crear_producto):
    producto_id = crear_producto(stock=1)
    respuesta = comprar(producto_id, 2)
    assert respuesta.status_code == 409
    assert stock_y_saldo(producto_id) == (1, 1)
    assert pedidos_del_producto(producto_id) == 0  # el pedido se deshizo con la transacción


def test_producto_inexistente_responde_404():
    assert comprar(999_999, 1).status_code == 404


@pytest.mark.parametrize("cantidad", [0, -1, compras.MAXIMO_POR_COMPRA + 1, "dos"])
def test_cantidad_invalida_responde_422(crear_producto, cantidad):
    producto_id = crear_producto(stock=50)
    assert comprar(producto_id, cantidad).status_code == 422
    assert stock_y_saldo(producto_id) == (50, 50)


@pytest.mark.parametrize("rol", ["operador", "administrador"])
def test_solo_el_cliente_puede_comprar(crear_producto, rol):
    producto_id = crear_producto(stock=1)
    assert comprar(producto_id, 1, rol=rol).status_code == 403


def test_sin_sesion_no_se_puede_comprar():
    respuesta = cliente_http.post(
        "/pedidos", json={"items": [{"producto_id": 1, "cantidad": 1}]}, headers={"Idempotency-Key": "x"}
    )
    assert respuesta.status_code == 401


# --- Concurrencia (prueba de cierre) ------------------------------------------


def test_100_compras_simultaneas_de_la_ultima_unidad_dan_un_solo_exito(crear_producto):
    producto_id = crear_producto(stock=1)
    with Sesion() as sesion:
        usuario_id = sesion.scalar(select(Usuario.id).where(Usuario.rol == "cliente"))

    solicitudes = 100
    largada = threading.Barrier(solicitudes)  # todas parten a la vez

    def intentar() -> bool:
        largada.wait()
        with Sesion() as sesion:
            try:
                compras.iniciar_compra(sesion, usuario_id, {producto_id: 1})
                return True
            except compras.StockInsuficiente:
                return False

    with ThreadPoolExecutor(max_workers=solicitudes) as ejecutor:
        resultados = list(ejecutor.map(lambda _: intentar(), range(solicitudes)))

    assert resultados.count(True) == 1
    assert resultados.count(False) == solicitudes - 1
    assert stock_y_saldo(producto_id) == (0, 0)
    assert pedidos_del_producto(producto_id) == 1
