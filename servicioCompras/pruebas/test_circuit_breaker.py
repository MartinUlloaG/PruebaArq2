"""Circuit Breaker: cerrado -> abierto -> semiabierto -> cerrado. Sin red ni BD.

El reloj es falso: se avanza a mano en vez de esperar segundos de verdad.
"""

import pytest

from app.infraestructura.circuit_breaker import CircuitBreaker, CircuitoAbierto


class Reloj:
    def __init__(self):
        self.ahora = 0.0

    def __call__(self) -> float:
        return self.ahora


def _falla():
    raise ConnectionError("servicio caído")


@pytest.fixture
def reloj():
    return Reloj()


@pytest.fixture
def circuito(reloj):
    return CircuitBreaker("prueba", umbral_fallas=3, segundos_abierto=10, reloj=reloj)


def test_se_abre_tras_el_umbral_y_rechaza_sin_llamar(circuito):
    for _ in range(3):
        with pytest.raises(ConnectionError):
            circuito.llamar(_falla)
    assert circuito.estado == "abierto"

    llamadas = []
    with pytest.raises(CircuitoAbierto):
        circuito.llamar(lambda: llamadas.append(1))
    assert llamadas == []  # ni siquiera se intentó


def test_un_exito_reinicia_la_cuenta_de_fallas(circuito):
    for _ in range(2):
        with pytest.raises(ConnectionError):
            circuito.llamar(_falla)
    circuito.llamar(lambda: "ok")
    with pytest.raises(ConnectionError):
        circuito.llamar(_falla)
    assert circuito.estado == "cerrado"


def test_pasado_el_tiempo_prueba_una_vez_y_se_cierra_si_resulta(circuito, reloj):
    for _ in range(3):
        with pytest.raises(ConnectionError):
            circuito.llamar(_falla)
    reloj.ahora = 10
    assert circuito.estado == "semiabierto"
    assert circuito.llamar(lambda: "ok") == "ok"
    assert circuito.estado == "cerrado"


def test_si_la_prueba_falla_vuelve_a_abrirse(circuito, reloj):
    for _ in range(3):
        with pytest.raises(ConnectionError):
            circuito.llamar(_falla)
    reloj.ahora = 10
    with pytest.raises(ConnectionError):
        circuito.llamar(_falla)  # basta una falla en semiabierto
    assert circuito.estado == "abierto"
