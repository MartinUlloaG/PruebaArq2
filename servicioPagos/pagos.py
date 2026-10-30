"""Servicio de pagos: el participante de la Saga que habla con la pasarela.

Lee pagos.solicitudes, llama a la pasarela externa (REST, con tiempo límite y Circuit
Breaker) y publica en pagos.resultados. Hay dos tipos de solicitud, como en una
pasarela real:
- "iniciar": crea la transacción en la pasarela y publica el token y la URL donde paga
  el comprador ("transaccion_creada").
- "confirmar": el comprador ya volvió de la pasarela; se confirma y recién ahí se cobra.
  Publica si se cobró o no ("resultado").
Los mensajes de un pedido van con la clave del pedido, así llegan en orden.

- Si la pasarela no responde, se reintenta esperando 1, 2 y 4 segundos. Siempre con la
  misma clave de idempotencia: si el primer intento sí alcanzó a cobrar, el reintento
  recibe esa misma respuesta y no se cobra dos veces.
- Si se agotan los intentos, la solicitud va a la DLQ (pagos.muertos) y no se publica
  resultado: el servicio de compras devuelve el stock cuando vence la reserva.
- No tiene base de datos propia: la idempotencia la dan las claves (la de la pasarela
  y el id_evento del resultado, que el servicio de compras descarta si llega repetido).

Uso (con Kafka y la pasarela arriba):  python pagos.py
"""

import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
from confluent_kafka import Consumer, KafkaException, Producer
from confluent_kafka.admin import AdminClient, NewTopic

from circuit_breaker import CircuitBreaker, CircuitoAbierto

KAFKA = {"bootstrap.servers": os.environ.get("KAFKA_SERVIDORES", "127.0.0.1:9092"), "log_level": 3}
PASARELA_URL = os.environ.get("PASARELA_URL", "http://127.0.0.1:8001")
SEGUNDOS_LIMITE = 2

SOLICITUDES_PAGO = "pagos.solicitudes"
RESULTADOS_PAGO = "pagos.resultados"
MUERTOS = "pagos.muertos"

registro = logging.getLogger("servicio-pagos")

# Estado en vivo (GET http://127.0.0.1:8002/estado): lo lee la simulación de 100 mil
# para mostrar el Circuit Breaker de verdad, no un dibujo.
PUERTO_ESTADO = int(os.environ.get("PAGOS_PUERTO_ESTADO", 8002))
estadisticas = {"procesados": 0, "reintentos": 0, "a_la_dlq": 0}


class PasarelaNoDisponible(Exception):
    pass


class ClientePasarela:
    """Adapter: traduce la API HTTP de la pasarela a una llamada simple."""

    def __init__(self, http: httpx.Client, circuito: CircuitBreaker):
        self.http = http
        self.circuito = circuito

    def crear_transaccion(self, solicitud: dict) -> dict:
        cuerpo = {k: solicitud[k] for k in ("pedido_id", "monto", "url_retorno", "pagar_antes_de")}
        return self._post("/transacciones", cuerpo, solicitud["clave_idempotencia"] + "-crear")

    def confirmar(self, token: str, clave_idempotencia: str) -> dict:
        return self._post(f"/transacciones/{token}/confirmar", {}, clave_idempotencia)

    def _post(self, ruta: str, cuerpo: dict, clave_idempotencia: str) -> dict:
        def llamada() -> dict:
            try:
                respuesta = self.http.post(ruta, json=cuerpo, headers={"Idempotency-Key": clave_idempotencia})
                respuesta.raise_for_status()
                return respuesta.json()
            except (httpx.HTTPError, ValueError) as error:
                # Solo esto cuenta como falla del Circuit Breaker: un pago rechazado
                # es una respuesta válida de la pasarela, no una falla.
                raise PasarelaNoDisponible(str(error)) from error

        try:
            return self.circuito.llamar(llamada)
        except CircuitoAbierto as error:
            raise PasarelaNoDisponible(str(error)) from error


def procesar_solicitud(solicitud: dict, pasarela: ClientePasarela) -> dict:
    """Llama a la pasarela y arma el evento para el núcleo. Lanza PasarelaNoDisponible si
    no se pudo. Los id_evento son fijos por pedido: si se publica dos veces, el núcleo
    descarta el segundo."""
    pedido_id = solicitud["pedido_id"]
    if solicitud["tipo"] == "iniciar":
        respuesta = pasarela.crear_transaccion(solicitud)
        return {
            "id_evento": f"transaccion-pedido-{pedido_id}",
            "tipo": "transaccion_creada",
            "pedido_id": pedido_id,
            "token": respuesta["token"],
            "url_pago": respuesta["url"],
        }
    if solicitud["tipo"] == "confirmar":
        # Misma clave siempre: si se reintenta o Kafka entrega dos veces, se cobra una vez.
        respuesta = pasarela.confirmar(solicitud["token"], solicitud["clave_idempotencia"])
        return {
            "id_evento": f"resultado-pedido-{pedido_id}",
            "tipo": "resultado",
            "pedido_id": pedido_id,
            "autorizado": respuesta["autorizado"],
            "referencia": respuesta.get("referencia"),
            "medio": respuesta.get("medio"),
            "motivo": respuesta.get("motivo"),
        }
    raise ValueError(f"Tipo de solicitud desconocido: {solicitud['tipo']}")


def crear_topicos() -> None:
    admin = AdminClient(KAFKA)
    nuevos = [NewTopic(t, num_partitions=3, replication_factor=1) for t in (SOLICITUDES_PAGO, RESULTADOS_PAGO, MUERTOS)]
    for futuro in admin.create_topics(nuevos).values():
        try:
            futuro.result()
        except KafkaException as error:
            if "TOPIC_ALREADY_EXISTS" not in str(error):
                raise


def atender(
    pasarela: ClientePasarela,
    detener: threading.Event,
    grupo: str = "servicio-pagos",
    intentos: int = 4,
    espera_inicial: float = 1,
) -> None:
    """Bucle principal: solicitud -> cobro -> resultado, con reintentos y DLQ."""
    consumidor = Consumer(
        {**KAFKA, "group.id": grupo, "enable.auto.commit": False, "auto.offset.reset": "earliest"}
    )
    productor = Producer(KAFKA)
    consumidor.subscribe([SOLICITUDES_PAGO])
    try:
        while not detener.is_set():
            mensaje = consumidor.poll(0.5)
            if mensaje is None:
                continue
            if mensaje.error():
                registro.warning("Kafka: %s", mensaje.error())
                continue
            solicitud = json.loads(mensaje.value())
            for intento in range(intentos):
                try:
                    resultado = procesar_solicitud(solicitud, pasarela)
                    productor.produce(RESULTADOS_PAGO, key=mensaje.key(), value=json.dumps(resultado))
                    productor.flush(10)
                    estadisticas["procesados"] += 1
                    registro.info("Pedido %s: %s", solicitud["pedido_id"], resultado["tipo"])
                    break
                except (KeyError, ValueError) as error:
                    # Mensaje mal formado: reintentar no lo arregla, va directo a la DLQ.
                    registro.error("Solicitud mal formada a la DLQ: %s", error)
                    muerto = {"topico_origen": SOLICITUDES_PAGO, "error": repr(error), "evento": solicitud}
                    productor.produce(MUERTOS, key=mensaje.key(), value=json.dumps(muerto))
                    productor.flush(10)
                    estadisticas["a_la_dlq"] += 1
                    break
                except PasarelaNoDisponible as error:
                    if intento == intentos - 1:
                        registro.error("Pedido %s a la DLQ: %s", solicitud["pedido_id"], error)
                        muerto = {"topico_origen": SOLICITUDES_PAGO, "error": str(error), "evento": solicitud}
                        productor.produce(MUERTOS, key=mensaje.key(), value=json.dumps(muerto))
                        productor.flush(10)
                        estadisticas["a_la_dlq"] += 1
                    else:
                        estadisticas["reintentos"] += 1
                        detener.wait(espera_inicial * 2**intento)
            try:
                consumidor.commit(mensaje, asynchronous=False)  # recién aquí se da por leído
            except KafkaException as error:
                # Rebalanceo del grupo: el mensaje se volverá a entregar y las claves de
                # idempotencia evitan cobrar dos veces. El bucle no se puede morir por esto.
                registro.warning("No se pudo confirmar el offset, se releerá: %s", error)
    finally:
        consumidor.close()


def servir_estado(pasarela: ClientePasarela) -> None:
    """Responde el estado del circuito y los contadores en un hilo aparte."""

    class Estado(BaseHTTPRequestHandler):
        def do_GET(self):
            circuito = pasarela.circuito
            cuerpo = json.dumps({"circuito": circuito.estado, "aperturas": circuito.aperturas, **estadisticas})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(cuerpo.encode())

        def log_message(self, *_):
            pass  # sin una línea por consulta en la consola

    servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO_ESTADO), Estado)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    crear_topicos()
    pasarela = ClientePasarela(
        httpx.Client(base_url=PASARELA_URL, timeout=SEGUNDOS_LIMITE),
        CircuitBreaker("pasarela de pago", umbral_fallas=3, segundos_abierto=10),
    )
    detener = threading.Event()
    servir_estado(pasarela)
    registro.info("Servicio de pagos escuchando %s (estado en :%s/estado)", SOLICITUDES_PAGO, PUERTO_ESTADO)
    try:
        atender(pasarela, detener)
    except KeyboardInterrupt:
        detener.set()
