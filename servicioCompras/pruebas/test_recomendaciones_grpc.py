"""Recomendaciones por gRPC y aislamiento de fallos (el servicio secundario se puede caer).

Se levanta un servidor gRPC de prueba con el mismo contrato (protos/recomendaciones.proto).
"""

import time
from concurrent import futures

import grpc
import pytest

from ayudantes import cliente_http, encabezado
from app.api.dependencias import obtener_recomendaciones
from app.contratos import recomendaciones_pb2, recomendaciones_pb2_grpc
from app.infraestructura.catalogo_documental import RepositorioCatalogo
from app.infraestructura.circuit_breaker import CircuitBreaker
from app.infraestructura.servicios_externos import ClienteRecomendaciones
from app.principal import app

PUERTO_PRUEBA = "127.0.0.1:50999"


@pytest.fixture
def usar_cliente():
    def usar(direccion: str) -> ClienteRecomendaciones:
        cliente = ClienteRecomendaciones(direccion, CircuitBreaker("recomendaciones", umbral_fallas=3), 1)
        app.dependency_overrides[obtener_recomendaciones] = lambda: cliente
        return cliente

    yield usar
    app.dependency_overrides.pop(obtener_recomendaciones, None)


def test_las_recomendaciones_llegan_por_grpc(usar_cliente):
    ids = [p["producto_id"] for p in RepositorioCatalogo().listar() if p["disponibles"] > 0][:2]

    class Falso(recomendaciones_pb2_grpc.RecomendacionesServicer):
        def Destacados(self, solicitud, contexto):
            return recomendaciones_pb2.ListaDestacados(producto_ids=ids)

    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    recomendaciones_pb2_grpc.add_RecomendacionesServicer_to_server(Falso(), servidor)
    servidor.add_insecure_port(PUERTO_PRUEBA)
    servidor.start()
    try:
        usar_cliente(PUERTO_PRUEBA)
        respuesta = cliente_http.get("/recomendaciones", headers=encabezado("cliente")).json()
    finally:
        servidor.stop(grace=0)

    assert respuesta["disponible"] is True
    assert [p["producto_id"] for p in respuesta["productos"]] == ids


def test_con_recomendaciones_caido_el_catalogo_sigue_y_el_circuito_se_abre(usar_cliente):
    cliente = usar_cliente(PUERTO_PRUEBA)  # no hay nadie escuchando en ese puerto
    h = encabezado("cliente")

    respuestas = [cliente_http.get("/recomendaciones", headers=h).json() for _ in range(3)]
    inicio = time.perf_counter()
    cuarta = cliente_http.get("/recomendaciones", headers=h).json()
    demora = time.perf_counter() - inicio

    assert all(r == {"disponible": False, "productos": []} for r in respuestas + [cuarta])
    assert cliente.circuito.estado == "abierto"
    assert demora < 0.5  # con el circuito abierto ni siquiera intenta conectarse
    assert cliente_http.get("/catalogo", headers=h).status_code == 200  # el catálogo no se entera
