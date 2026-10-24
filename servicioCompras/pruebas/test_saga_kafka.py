"""La Saga completa pasando por Kafka de verdad (necesita el contenedor de Kafka arriba).

Corre en hilos lo mismo que corre en producción: el relay del outbox y el consumidor de
resultados del servicio de compras, y el bucle del servicio de pagos. Solo la pasarela
corre dentro de la prueba (TestClient). Si Kafka no está, la prueba se salta.
"""

import threading
import time

import pytest
from confluent_kafka.admin import AdminClient
from fastapi.testclient import TestClient

from ayudantes import comprar, estado_pedido_y_pago, stock_y_saldo
import pagos
import pasarela as pasarela_simulada
from app import trabajadores
from app.infraestructura import mensajeria
from circuit_breaker import CircuitBreaker


def _kafka_arriba() -> bool:
    try:
        AdminClient(mensajeria.BASE).list_topics(timeout=3)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _kafka_arriba(), reason="Kafka no está arriba (docker compose up -d)")


@pytest.fixture
def saga():
    """Levanta los hilos de la Saga y la pasarela en modo "aprueba". Devuelve el http de la pasarela."""
    pasarela_simulada._respuestas.clear()
    pasarela_simulada._cobros.clear()
    pasarela_simulada._estado["modo"] = "aprueba"
    http = TestClient(pasarela_simulada.app)
    cliente = pagos.ClientePasarela(http, CircuitBreaker("pasarela"))

    detener = trabajadores.iniciar()
    threading.Thread(target=pagos.atender, args=(cliente, detener), daemon=True).start()
    yield http
    detener.set()
    time.sleep(1)  # que los consumidores alcancen a cerrarse y salir del grupo


def _esperar_estado(pedido_id: int, segundos: float = 30) -> str:
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        estado, _ = estado_pedido_y_pago(pedido_id)
        if estado != "stock_reservado":
            return estado
        time.sleep(0.3)
    return estado


def test_la_compra_viaja_por_kafka_y_queda_pagada(crear_producto, saga):
    producto_id = crear_producto(stock=3)
    pedido_id = comprar(producto_id, 1).json()["pedido_id"]

    assert _esperar_estado(pedido_id) == "pagado"
    assert estado_pedido_y_pago(pedido_id) == ("pagado", "autorizado")
    assert stock_y_saldo(producto_id) == (2, 2)
    assert saga.get("/cobros").json()["total"] == 1


def test_pago_rechazado_por_kafka_devuelve_el_stock(crear_producto, saga):
    saga.put("/simulacion", json={"modo": "rechaza"})
    producto_id = crear_producto(stock=3)
    pedido_id = comprar(producto_id, 2).json()["pedido_id"]

    assert _esperar_estado(pedido_id) == "fallido"
    assert stock_y_saldo(producto_id) == (3, 3)
