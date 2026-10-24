"""Clientes HTTP hacia los servicios satélite (patrón Adapter).

Traducen la API HTTP de cada servicio a una llamada simple para el dominio, y pasan
siempre por su Circuit Breaker. El dominio no sabe de HTTP ni de httpx.

Regla para el Circuit Breaker: solo se lanza excepción ante problemas de
infraestructura (no responde, tiempo límite, 5xx). Un pago rechazado es una
respuesta válida y no cuenta como falla.
"""

from dataclasses import dataclass

import httpx

from app.configuracion import configuracion
from app.infraestructura.circuit_breaker import CircuitBreaker, CircuitoAbierto


class ServicioNoDisponible(Exception):
    """El servicio externo no respondió bien, o su circuito está abierto."""


@dataclass(frozen=True)
class ResultadoPago:
    autorizado: bool
    referencia: str | None
    motivo: str | None


def _pedir(circuito: CircuitBreaker, http: httpx.Client, metodo: str, ruta: str, **opciones) -> dict:
    def llamada() -> dict:
        try:
            respuesta = http.request(metodo, ruta, **opciones)
            respuesta.raise_for_status()
            return respuesta.json()
        except (httpx.HTTPError, ValueError) as error:  # ValueError: el cuerpo no era JSON
            raise ServicioNoDisponible(f"{circuito.nombre}: {error}") from error

    try:
        return circuito.llamar(llamada)
    except CircuitoAbierto as error:
        raise ServicioNoDisponible(str(error)) from error


class ClientePasarela:
    def __init__(self, http: httpx.Client, circuito: CircuitBreaker):
        self.http = http
        self.circuito = circuito

    def autorizar(self, pedido_id: int, monto: int, clave_idempotencia: str) -> ResultadoPago:
        """La clave viaja a la pasarela: si este cobro se reintenta, ella no cobra dos veces."""
        datos = _pedir(
            self.circuito,
            self.http,
            "POST",
            "/autorizaciones",
            json={"pedido_id": pedido_id, "monto": monto},
            headers={"Idempotency-Key": clave_idempotencia},
        )
        return ResultadoPago(datos["autorizado"], datos.get("referencia"), datos.get("motivo"))


class ClienteRecomendaciones:
    def __init__(self, http: httpx.Client, circuito: CircuitBreaker):
        self.http = http
        self.circuito = circuito

    def destacados(self) -> list[int]:
        return _pedir(self.circuito, self.http, "GET", "/recomendaciones")["producto_ids"]


# Una instancia por servicio para toda la app: el Circuit Breaker debe recordar las
# fallas entre solicitudes. Los endpoints las reciben por inyección de dependencias.
pasarela = ClientePasarela(
    httpx.Client(base_url=configuracion.pasarela_url, timeout=configuracion.pasarela_segundos_limite),
    CircuitBreaker("pasarela de pago"),
)
recomendaciones = ClienteRecomendaciones(
    httpx.Client(
        base_url=configuracion.recomendaciones_url,
        timeout=configuracion.recomendaciones_segundos_limite,
    ),
    CircuitBreaker("recomendaciones"),
)
