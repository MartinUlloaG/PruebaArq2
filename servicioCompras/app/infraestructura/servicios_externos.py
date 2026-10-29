"""Clientes hacia los servicios satélite internos (patrón Adapter).

Recomendaciones se llama por gRPC (protos/recomendaciones.proto): es un servicio
interno y la llamada es síncrona, justo donde la Eva 1 puso gRPC. El cliente traduce
el mensaje de protobuf a una lista simple de ids, así el resto del núcleo no sabe de gRPC.

Toda llamada lleva tiempo límite (deadline) y pasa por su Circuit Breaker. Regla: solo
se lanza excepción ante problemas de infraestructura (caído, tiempo límite, error).
"""

import grpc

from app.configuracion import configuracion
from app.contratos import recomendaciones_pb2, recomendaciones_pb2_grpc
from app.infraestructura.circuit_breaker import CircuitBreaker, CircuitoAbierto


class ServicioNoDisponible(Exception):
    """El servicio no respondió bien, o su circuito está abierto."""


class ClienteRecomendaciones:
    def __init__(self, direccion: str, circuito: CircuitBreaker, segundos_limite: float):
        self.canal = grpc.insecure_channel(direccion)  # solo local; mTLS queda en la arquitectura objetivo
        self.stub = recomendaciones_pb2_grpc.RecomendacionesStub(self.canal)
        self.circuito = circuito
        self.segundos_limite = segundos_limite

    def destacados(self, limite: int = 4) -> list[int]:
        def llamada() -> list[int]:
            try:
                respuesta = self.stub.Destacados(
                    recomendaciones_pb2.SolicitudDestacados(limite=limite), timeout=self.segundos_limite
                )
                return list(respuesta.producto_ids)
            except grpc.RpcError as error:  # UNAVAILABLE si está caído, DEADLINE_EXCEEDED si es lento
                raise ServicioNoDisponible(f"{self.circuito.nombre}: {error.code().name}") from error

        try:
            return self.circuito.llamar(llamada)
        except CircuitoAbierto as error:
            raise ServicioNoDisponible(str(error)) from error


# Una instancia para toda la app: el Circuit Breaker debe recordar las fallas entre
# solicitudes. Los endpoints la reciben por inyección de dependencias.
recomendaciones = ClienteRecomendaciones(
    configuracion.recomendaciones_grpc,
    CircuitBreaker("recomendaciones"),
    configuracion.recomendaciones_segundos_limite,
)
