import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import trabajadores
from app.api import administracion, autenticacion, catalogo, inventario, pedidos, recomendaciones
from app.configuracion import configuracion
from app.infraestructura import servicios_externos


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    # Los hilos de Kafka corren mientras la app está arriba.
    detener = trabajadores.iniciar() if configuracion.kafka_activo else None
    yield
    if detener:
        detener.set()


app = FastAPI(title="Servicio de compras", lifespan=ciclo_de_vida)

app.include_router(autenticacion.enrutador)
app.include_router(catalogo.enrutador)
app.include_router(recomendaciones.enrutador)
app.include_router(pedidos.enrutador)
app.include_router(inventario.enrutador)
app.include_router(administracion.enrutador)


@app.get("/salud")
def salud():
    # Lo muestra la simulación de 100 mil: el estado del circuito, el TTL de la reserva y
    # qué copia del núcleo respondió (con --workers 4 se ven las 4 réplicas).
    return {
        "estado": "ok",
        "circuito_recomendaciones": servicios_externos.recomendaciones.circuito.estado,
        "segundos_reserva": configuracion.segundos_reserva,
        "proceso": os.getpid(),
    }
