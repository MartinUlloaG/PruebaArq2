"""Clientes HTTP hacia los servicios satélite (patrón Adapter).

Traducen la API HTTP de cada servicio a una llamada simple, y pasan siempre por su
Circuit Breaker. Regla: solo se lanza excepción ante problemas de infraestructura
(no responde, tiempo límite, 5xx).
"""

import httpx

from app.configuracion import configuracion
from app.infraestructura.circuit_breaker import CircuitBreaker, CircuitoAbierto


class ServicioNoDisponible(Exception):
    """El servicio externo no respondió bien, o su circuito está abierto."""


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


class ClienteRecomendaciones:
    def __init__(self, http: httpx.Client, circuito: CircuitBreaker):
        self.http = http
        self.circuito = circuito

    def destacados(self) -> list[int]:
        return _pedir(self.circuito, self.http, "GET", "/recomendaciones")["producto_ids"]


# Una instancia para toda la app: el Circuit Breaker debe recordar las fallas entre
# solicitudes. Los endpoints la reciben por inyección de dependencias.
recomendaciones = ClienteRecomendaciones(
    httpx.Client(
        base_url=configuracion.recomendaciones_url,
        timeout=configuracion.recomendaciones_segundos_limite,
    ),
    CircuitBreaker("recomendaciones"),
)
