"""Kafka: tópicos de la Saga, relay del outbox y consumidor con reintentos y DLQ.

Reglas de la Eva 1 que se aplican aquí:
- Tópicos separados por criticidad: los pagos tienen sus propios tópicos.
- Outbox: nadie publica directo; el relay lee la tabla outbox y publica.
- Reintentos con espera creciente y, si se agotan, Dead Letter Queue (pagos.muertos),
  para no dejar trabado el tópico por un mensaje que no se puede procesar.
- Consumidores idempotentes: eso lo hace quien maneja el mensaje (ver dominio/compras.py).
"""

import json
import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime

from confluent_kafka import Consumer, KafkaException, Producer
from confluent_kafka.admin import AdminClient, NewTopic
from sqlalchemy import select

from app.configuracion import configuracion
from app.infraestructura.base import Sesion
from app.infraestructura.modelos import Outbox

registro = logging.getLogger("mensajeria")

SOLICITUDES_PAGO = "pagos.solicitudes"  # núcleo -> servicio de pagos
RESULTADOS_PAGO = "pagos.resultados"  # servicio de pagos -> núcleo
MUERTOS = "pagos.muertos"  # Dead Letter Queue: se revisa a mano
TOPICOS = (SOLICITUDES_PAGO, RESULTADOS_PAGO, MUERTOS)

# log_level 3 = solo errores: librdkafka anota cada reconexión mientras el broker parte.
BASE = {"bootstrap.servers": configuracion.kafka_servidores, "log_level": 3}


def crear_topicos() -> None:
    """Crea los tópicos si no existen. 3 particiones: la clave (el pedido) elige una,
    así los mensajes de un mismo pedido llegan en orden."""
    admin = AdminClient(BASE)
    pedidos = admin.create_topics(
        [NewTopic(t, num_partitions=3, replication_factor=1) for t in TOPICOS]
    )
    for topico, futuro in pedidos.items():
        try:
            futuro.result()
        except KafkaException as error:
            if "TOPIC_ALREADY_EXISTS" not in str(error):
                raise


def publicar_pendientes(productor: Producer, limite: int = 100) -> int:
    """Una pasada del relay: publica lo pendiente del outbox y lo marca publicado.

    Si Kafka falla, la transacción se deshace y los mensajes siguen pendientes para la
    próxima pasada. Si el proceso se cae justo después de publicar y antes de marcar,
    el mensaje se publica dos veces: por eso los consumidores son idempotentes.
    """
    with Sesion.begin() as sesion:
        pendientes = list(
            sesion.scalars(
                select(Outbox)
                .where(Outbox.publicado_en.is_(None))
                .order_by(Outbox.id)
                .limit(limite)
                .with_for_update(skip_locked=True)  # dos relays no publican lo mismo
            )
        )
        errores = []
        for mensaje in pendientes:
            productor.produce(
                mensaje.topico,
                key=mensaje.clave,
                value=json.dumps(mensaje.contenido),
                on_delivery=lambda error, _: error and errores.append(error),
            )
        if productor.flush(10) > 0 or errores:
            raise KafkaException(f"No se pudieron publicar los mensajes: {errores}")
        ahora = datetime.now(UTC)
        for mensaje in pendientes:
            mensaje.publicado_en = ahora
        return len(pendientes)


def relay_outbox(detener: threading.Event, cada_segundos: float = 0.5) -> None:
    productor = Producer(BASE)
    while not detener.is_set():
        try:
            publicar_pendientes(productor)
        except Exception:
            registro.exception("Relay del outbox: falló una pasada, se reintenta")
        detener.wait(cada_segundos)


def consumir(
    topico: str,
    grupo: str,
    manejar: Callable[[dict], None],
    detener: threading.Event,
    intentos: int = 4,
    espera_inicial: float = 1,
) -> None:
    """Lee `topico` y llama a `manejar` con cada mensaje.

    Si `manejar` falla, se reintenta esperando 1, 2, 4... segundos. Si falla todas las
    veces, el mensaje va a la DLQ y se sigue con el siguiente. El offset se confirma
    recién después de procesar: si el proceso se cae a la mitad, el mensaje se relee.
    """
    consumidor = Consumer(
        {**BASE, "group.id": grupo, "enable.auto.commit": False, "auto.offset.reset": "earliest"}
    )
    productor = Producer(BASE)
    consumidor.subscribe([topico])
    try:
        while not detener.is_set():
            mensaje = consumidor.poll(0.5)
            if mensaje is None:
                continue
            if mensaje.error():
                registro.warning("Kafka: %s", mensaje.error())
                continue
            evento = json.loads(mensaje.value())
            for intento in range(intentos):
                try:
                    manejar(evento)
                    break
                except Exception as error:
                    if intento == intentos - 1:
                        registro.error("A la DLQ tras %s intentos: %s", intentos, error)
                        muerto = {"topico_origen": topico, "error": str(error), "evento": evento}
                        productor.produce(MUERTOS, key=mensaje.key(), value=json.dumps(muerto))
                        productor.flush(10)
                    else:
                        detener.wait(espera_inicial * 2**intento)
            consumidor.commit(mensaje, asynchronous=False)
    finally:
        consumidor.close()
