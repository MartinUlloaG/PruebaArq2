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

from ayudantes import cliente_http, comprar, encabezado, estado_pedido_y_pago, stock_y_saldo
import pagos
import pasarela as pasarela_simulada
from app import trabajadores
from app.infraestructura import mensajeria
from app.infraestructura.catalogo_documental import RepositorioCatalogo
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
    """Levanta los hilos de la Saga y una pasarela limpia. Devuelve el http de la pasarela."""
    pasarela_simulada._respuestas.clear()
    pasarela_simulada._cobros.clear()
    pasarela_simulada._tarjetas.update(pasarela_simulada._tarjetas_demo())
    pasarela_simulada._estado["modo"] = "normal"
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


def _esperar_url_de_pago(pedido_id: int, segundos: float = 30) -> str:
    """Paso 2: lo que hace la interfaz antes de mandar al comprador a la pasarela."""
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        pago = cliente_http.get(f"/pedidos/{pedido_id}", headers=encabezado("cliente")).json()["pago"]
        if pago["url_pago"]:
            return pago["url_pago"].rsplit("/", 1)[1]  # el token
        time.sleep(0.3)
    raise AssertionError("La transacción no se creó a tiempo")


def _pagar_y_volver(pasarela, pedido_id: int, caso: str) -> None:
    """El comprador paga con crédito en la página de la pasarela y vuelve a la tienda."""
    token = _esperar_url_de_pago(pedido_id)
    tarjeta = next(t for t in pasarela.get("/tarjetas-prueba").json() if t["caso"] == caso)
    datos = {"tipo": "credito", "numero": tarjeta["numero"], "vencimiento": tarjeta["vencimiento"], "cvv": tarjeta["cvv"]}
    pasarela.post(f"/transacciones/{token}/tarjeta", json=datos)
    for _ in range(2):  # volvió y recargó la página: la confirmación se pide una sola vez
        respuesta = cliente_http.post("/pedidos/confirmar-pago", json={"token": token}, headers=encabezado("cliente"))
        assert respuesta.status_code == 202


def test_la_compra_viaja_por_kafka_y_queda_pagada(crear_producto, saga):
    producto_id = crear_producto(stock=3)
    pedido_id = comprar(producto_id, 1).json()["pedido_id"]
    _pagar_y_volver(saga, pedido_id, "Crédito: se aprueba")

    assert _esperar_estado(pedido_id) == "pagado"
    assert estado_pedido_y_pago(pedido_id) == ("pagado", "autorizado")
    assert stock_y_saldo(producto_id) == (2, 2)
    assert saga.get("/cobros").json()["total"] == 1


def test_pago_rechazado_por_kafka_devuelve_el_stock(crear_producto, saga):
    producto_id = crear_producto(stock=3)
    pedido_id = comprar(producto_id, 2).json()["pedido_id"]
    _pagar_y_volver(saga, pedido_id, "Crédito: cupo insuficiente")

    assert _esperar_estado(pedido_id) == "fallido"
    assert stock_y_saldo(producto_id) == (3, 3)  # la unidad vuelve al tiro, no espera el TTL


def test_el_stock_comprado_llega_al_catalogo_en_mongo(crear_producto, saga):
    """CQRS: la compra descuenta en Postgres y el proyector lleva ese stock a Mongo por Kafka."""
    producto_id = crear_producto(stock=5)
    catalogo = RepositorioCatalogo()
    catalogo.guardar(producto_id, {"nombre": "Prueba", "categoria": "Pruebas", "precio": 1000,
                                   "disponibles": 5, "version_stock": 0, "activo": True})
    try:
        comprar(producto_id, 2)  # la reserva ya descuenta, aunque todavía no se pague
        limite = time.monotonic() + 30
        while time.monotonic() < limite and catalogo.por_id([producto_id])[producto_id]["disponibles"] != 3:
            time.sleep(0.3)
        assert catalogo.por_id([producto_id])[producto_id]["disponibles"] == 3
    finally:
        catalogo.coleccion.delete_one({"_id": producto_id})
