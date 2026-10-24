"""Servicio de pagos (servicioPagos/pagos.py) contra la pasarela simulada de verdad.

La pasarela corre dentro de la prueba con TestClient en vez de en su propio puerto.
"""

import httpx
import pytest
from fastapi.testclient import TestClient

import ayudantes  # noqa: F401  (agrega las carpetas de los otros servicios al path)
import pagos
import pasarela as pasarela_simulada
from circuit_breaker import CircuitBreaker

SOLICITUD = {"id_evento": "solicitud-pedido-1", "pedido_id": 1, "monto": 5000, "clave_idempotencia": "pedido-1"}


@pytest.fixture
def pasarela():
    """Pasarela limpia en modo "aprueba". Devuelve (cliente del servicio de pagos, http de la pasarela)."""
    pasarela_simulada._respuestas.clear()
    pasarela_simulada._cobros.clear()
    pasarela_simulada._estado["modo"] = "aprueba"
    http = TestClient(pasarela_simulada.app)
    return pagos.ClientePasarela(http, CircuitBreaker("pasarela de prueba")), http


def test_pago_aprobado(pasarela):
    cliente, http = pasarela
    resultado = pagos.procesar_solicitud(SOLICITUD, cliente)
    assert resultado["autorizado"] is True
    assert resultado["id_evento"] == "resultado-pedido-1"
    assert http.get("/cobros").json()["total"] == 1


def test_pago_rechazado_no_cobra(pasarela):
    cliente, http = pasarela
    http.put("/simulacion", json={"modo": "rechaza"})
    resultado = pagos.procesar_solicitud(SOLICITUD, cliente)
    assert resultado["autorizado"] is False
    assert http.get("/cobros").json()["total"] == 0


def test_la_misma_solicitud_dos_veces_cobra_una_vez(pasarela):
    """Kafka puede entregar la solicitud dos veces: la clave evita el cobro doble."""
    cliente, http = pasarela
    primero = pagos.procesar_solicitud(SOLICITUD, cliente)
    segundo = pagos.procesar_solicitud(SOLICITUD, cliente)
    assert primero == segundo  # misma referencia de autorización
    assert http.get("/cobros").json()["total"] == 1


def test_pasarela_caida_lanza_error_para_reintentar(pasarela):
    cliente, http = pasarela
    http.put("/simulacion", json={"modo": "falla"})
    with pytest.raises(pagos.PasarelaNoDisponible):
        pagos.procesar_solicitud(SOLICITUD, cliente)


def test_tras_3_tiempos_limite_el_circuito_se_abre_y_no_llama_mas():
    llamadas = []

    def sin_respuesta(solicitud: httpx.Request) -> httpx.Response:
        llamadas.append(solicitud)
        raise httpx.ReadTimeout("la pasarela no respondió a tiempo", request=solicitud)

    http = httpx.Client(transport=httpx.MockTransport(sin_respuesta), base_url="http://pasarela")
    cliente = pagos.ClientePasarela(http, CircuitBreaker("pasarela lenta", umbral_fallas=3))

    for _ in range(5):
        with pytest.raises(pagos.PasarelaNoDisponible):
            pagos.procesar_solicitud(SOLICITUD, cliente)

    assert len(llamadas) == 3  # los intentos 4 y 5 no esperaron a la pasarela
    assert cliente.circuito.estado == "abierto"
