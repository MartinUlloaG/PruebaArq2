"""Hilos de fondo del servicio de compras. Arrancan y se detienen con la app (principal.py).

- relay del outbox: publica en Kafka lo que dejó la compra en la tabla outbox.
- consumidor de resultados: aplica el resultado del pago (paso 3 de la Saga).
- vencedor de reservas: devuelve el stock de los pedidos cuyo pago no llegó a tiempo.
- proyector del catálogo: copia cada cambio de stock de Postgres a Mongo (CQRS).
"""

import logging
import threading

from app.configuracion import configuracion
from app.dominio import compras
from app.infraestructura import mensajeria
from app.infraestructura.base import Sesion
from app.infraestructura.catalogo_documental import RepositorioCatalogo

registro = logging.getLogger("trabajadores")


def _aplicar_resultado(evento: dict) -> None:
    with Sesion() as sesion:
        compras.aplicar_resultado_pago(sesion, evento)


def _proyectar_stock(evento: dict) -> None:
    RepositorioCatalogo().actualizar_stock(evento["producto_id"], evento["disponibles"], evento["version"])


def _vencer_reservas(detener: threading.Event, cada_segundos: float = 5) -> None:
    while not detener.is_set():
        try:
            with Sesion() as sesion:
                vencidas = compras.expirar_reservas(sesion, configuracion.segundos_reserva)
            if vencidas:
                registro.info("Reservas vencidas y stock devuelto: %s", vencidas)
        except Exception:
            registro.exception("Vencedor de reservas: falló una pasada")
        detener.wait(cada_segundos)


def iniciar() -> threading.Event:
    """Arranca los hilos. Devuelve el evento que hay que activar para detenerlos."""
    mensajeria.crear_topicos()
    detener = threading.Event()
    tareas = [
        (mensajeria.relay_outbox, (detener,)),
        (
            mensajeria.consumir,
            (mensajeria.RESULTADOS_PAGO, "servicio-compras", _aplicar_resultado, detener),
        ),
        (_vencer_reservas, (detener,)),
        (
            mensajeria.consumir,
            (mensajeria.CAMBIOS_STOCK, "proyector-catalogo", _proyectar_stock, detener),
        ),
    ]
    for funcion, argumentos in tareas:
        threading.Thread(target=funcion, args=argumentos, daemon=True).start()
    return detener
