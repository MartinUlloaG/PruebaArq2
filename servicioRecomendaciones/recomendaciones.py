"""Servicio de recomendaciones: el servicio SECUNDARIO del caso (gRPC, puerto 50051).

- Sirve Destacados por gRPC: los productos más vendidos. El contrato está en
  protos/recomendaciones.proto (de ahí salen recomendaciones_pb2*.py).
- Sabe qué se vende porque escucha el evento pedidos.pagados en Kafka. No lee la base
  de datos del servicio de compras: cada microservicio tiene sus propios datos.
- Guarda los conteos en memoria. Al arrancar relee los eventos desde el principio del
  tópico y reconstruye los conteos (por eso usa un grupo de Kafka nuevo cada vez).

Sirve para demostrar el aislamiento de fallos: si se apaga (Ctrl+C), el catálogo y la
compra siguen funcionando; el servicio de compras solo deja de mostrar las recomendaciones.

Uso (con Kafka arriba):  python recomendaciones.py
"""

import json
import logging
import os
import threading
import uuid
from collections import Counter
from concurrent import futures

import grpc
from confluent_kafka import Consumer

import recomendaciones_pb2
import recomendaciones_pb2_grpc

KAFKA = {"bootstrap.servers": os.environ.get("KAFKA_SERVIDORES", "127.0.0.1:9092"), "log_level": 3}
PUERTO = os.environ.get("RECOMENDACIONES_PUERTO", "50051")
PEDIDOS_PAGADOS = "pedidos.pagados"

registro = logging.getLogger("servicio-recomendaciones")

_candado = threading.Lock()
_vendidos = Counter()  # producto_id -> unidades vendidas
_eventos_vistos = set()  # consumidor idempotente: un evento repetido no se cuenta dos veces


def contar(evento: dict) -> None:
    id_evento = evento.get("id_evento")
    with _candado:
        if id_evento is None or id_evento in _eventos_vistos:
            return  # repetido, o de un formato viejo
        _eventos_vistos.add(id_evento)
        for item in evento["items"]:
            _vendidos[item["producto_id"]] += item["cantidad"]


def mas_vendidos(limite: int) -> list[int]:
    with _candado:
        return [producto_id for producto_id, _ in _vendidos.most_common(limite)]


class Recomendaciones(recomendaciones_pb2_grpc.RecomendacionesServicer):
    def Destacados(self, solicitud, contexto):
        limite = solicitud.limite or 4
        return recomendaciones_pb2.ListaDestacados(producto_ids=mas_vendidos(limite))


def escuchar_ventas(detener: threading.Event) -> None:
    consumidor = Consumer(
        {**KAFKA, "group.id": f"recomendaciones-{uuid.uuid4().hex}", "auto.offset.reset": "earliest", "enable.auto.commit": False}
    )
    consumidor.subscribe([PEDIDOS_PAGADOS])
    try:
        while not detener.is_set():
            mensaje = consumidor.poll(0.5)
            if mensaje is None or mensaje.error():
                continue
            contar(json.loads(mensaje.value()))
    finally:
        consumidor.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    detener = threading.Event()
    threading.Thread(target=escuchar_ventas, args=(detener,), daemon=True).start()

    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    recomendaciones_pb2_grpc.add_RecomendacionesServicer_to_server(Recomendaciones(), servidor)
    servidor.add_insecure_port(f"127.0.0.1:{PUERTO}")  # solo local; mTLS queda en la arquitectura objetivo
    servidor.start()
    registro.info("Recomendaciones por gRPC en 127.0.0.1:%s", PUERTO)
    try:
        servidor.wait_for_termination()
    except KeyboardInterrupt:
        detener.set()
        servidor.stop(grace=1)
