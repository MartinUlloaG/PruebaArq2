"""Servicio de pagos (servicioPagos/pagos.py) contra la pasarela simulada de verdad.

La pasarela corre dentro de la prueba con TestClient en vez de en su propio puerto.
El comprador "paga" llamando a los mismos endpoints que usa la página de pago.
"""

import httpx
import pytest
from fastapi.testclient import TestClient

import ayudantes  # noqa: F401  (agrega las carpetas de los otros servicios al path)
import pagos
import pasarela as pasarela_simulada
from circuit_breaker import CircuitBreaker

INICIAR = {
    "id_evento": "solicitud-pedido-1", "tipo": "iniciar", "pedido_id": 1, "monto": 5000,
    "clave_idempotencia": "pedido-1", "url_retorno": "http://tienda/pago/retorno", "pagar_antes_de": None,
}


@pytest.fixture
def pasarela():
    """Pasarela limpia. Devuelve (cliente del servicio de pagos, http de la pasarela)."""
    pasarela_simulada._respuestas.clear()
    pasarela_simulada._cobros.clear()
    pasarela_simulada._transacciones.clear()
    pasarela_simulada._tarjetas.update(pasarela_simulada._tarjetas_demo())
    pasarela_simulada._estado["modo"] = "normal"
    http = TestClient(pasarela_simulada.app)
    return pagos.ClientePasarela(http, CircuitBreaker("pasarela de prueba")), http


def _tarjeta(http, caso: str) -> dict:
    return next(t for t in http.get("/tarjetas-prueba").json() if t["caso"] == caso)


def _iniciar(cliente, pedido_id: int = 1) -> str:
    evento = pagos.procesar_solicitud({**INICIAR, "pedido_id": pedido_id, "clave_idempotencia": f"pedido-{pedido_id}"}, cliente)
    assert evento["tipo"] == "transaccion_creada"
    return evento["token"]


def _pagar_credito(http, token: str, tarjeta: dict, cvv: str | None = None) -> dict:
    datos = {"tipo": "credito", "numero": tarjeta["numero"], "vencimiento": tarjeta["vencimiento"], "cvv": cvv or tarjeta["cvv"]}
    return http.post(f"/transacciones/{token}/tarjeta", json=datos).json()


def _confirmar(cliente, token: str, pedido_id: int = 1) -> dict:
    solicitud = {"tipo": "confirmar", "pedido_id": pedido_id, "token": token, "clave_idempotencia": f"pedido-{pedido_id}"}
    return pagos.procesar_solicitud(solicitud, cliente)


def test_se_cobra_recien_cuando_el_comercio_confirma(pasarela):
    cliente, http = pasarela
    token = _iniciar(cliente)
    assert _pagar_credito(http, token, _tarjeta(http, "Crédito: se aprueba"))["estado"] == "autorizada"
    assert http.get("/cobros").json()["total"] == 0  # aprobado = retenido, todavía no cobrado

    resultado = _confirmar(cliente, token)
    assert resultado["autorizado"] is True
    assert resultado["medio"] == "Crédito VISA ****1111"  # la tienda solo ve el medio enmascarado
    assert http.get("/cobros").json()["total"] == 1


def test_la_misma_confirmacion_dos_veces_cobra_una_vez(pasarela):
    """Kafka puede entregar la solicitud dos veces: la clave evita el cobro doble."""
    cliente, http = pasarela
    token = _iniciar(cliente)
    _pagar_credito(http, token, _tarjeta(http, "Crédito: se aprueba"))
    assert _confirmar(cliente, token) == _confirmar(cliente, token)  # misma referencia
    assert http.get("/cobros").json()["total"] == 1


def test_3_cvv_malos_bloquean_la_tarjeta_y_no_se_cobra(pasarela):
    cliente, http = pasarela
    tarjeta = _tarjeta(http, "Crédito: se aprueba")
    token = _iniciar(cliente)
    assert "Te quedan 2" in _pagar_credito(http, token, tarjeta, cvv="000")["error"]
    assert "Te quedan 1" in _pagar_credito(http, token, tarjeta, cvv="000")["error"]
    tercero = _pagar_credito(http, token, tarjeta, cvv="000")
    assert tercero["estado"] == "rechazada" and "bloqueada" in tercero["motivo"]

    # Otra compra con la misma tarjeta, ahora con el CVV bueno: sigue bloqueada.
    otro = _iniciar(cliente, pedido_id=2)
    assert "bloqueada" in _pagar_credito(http, otro, tarjeta)["motivo"]
    assert _confirmar(cliente, token)["autorizado"] is False
    assert http.get("/cobros").json()["total"] == 0


def test_3_claves_malas_del_banco_bloquean_el_debito(pasarela):
    cliente, http = pasarela
    tarjeta = _tarjeta(http, "Débito: se aprueba")
    token = _iniciar(cliente)
    assert http.post(f"/transacciones/{token}/tarjeta", json={"tipo": "debito", "numero": tarjeta["numero"]}).json()["estado"] == "banco"
    for _ in range(3):
        respuesta = http.post(f"/transacciones/{token}/banco", json={"rut": tarjeta["rut"], "clave": "9999"}).json()
    assert respuesta["estado"] == "rechazada" and "bloqueado" in respuesta["motivo"]
    assert _confirmar(cliente, token)["autorizado"] is False


def test_si_nadie_confirma_a_tiempo_la_retencion_se_devuelve(pasarela, monkeypatch):
    """El comprador pagó pero nunca volvió a la tienda: no hay cobro y el cupo vuelve."""
    cliente, http = pasarela
    monkeypatch.setattr(pasarela_simulada, "SEGUNDOS_CONFIRMAR", -1)  # vence al tiro
    tarjeta = _tarjeta(http, "Crédito: se aprueba")
    cupo = pasarela_simulada._tarjetas[tarjeta["numero"]].saldo
    token = _iniciar(cliente)
    _pagar_credito(http, token, tarjeta)

    assert http.get(f"/transacciones/{token}").json()["estado"] == "rechazada"
    assert pasarela_simulada._tarjetas[tarjeta["numero"]].saldo == cupo
    assert _confirmar(cliente, token)["autorizado"] is False


def test_pasarela_caida_lanza_error_para_reintentar(pasarela):
    cliente, http = pasarela
    http.put("/simulacion", json={"modo": "falla"})
    with pytest.raises(pagos.PasarelaNoDisponible):
        pagos.procesar_solicitud(INICIAR, cliente)


def test_tras_3_tiempos_limite_el_circuito_se_abre_y_no_llama_mas():
    llamadas = []

    def sin_respuesta(solicitud: httpx.Request) -> httpx.Response:
        llamadas.append(solicitud)
        raise httpx.ReadTimeout("la pasarela no respondió a tiempo", request=solicitud)

    http = httpx.Client(transport=httpx.MockTransport(sin_respuesta), base_url="http://pasarela")
    cliente = pagos.ClientePasarela(http, CircuitBreaker("pasarela lenta", umbral_fallas=3))

    for _ in range(5):
        with pytest.raises(pagos.PasarelaNoDisponible):
            pagos.procesar_solicitud(INICIAR, cliente)

    assert len(llamadas) == 3  # los intentos 4 y 5 no esperaron a la pasarela
    assert cliente.circuito.estado == "abierto"
