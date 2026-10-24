from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import trabajadores
from app.api import administracion, autenticacion, catalogo, inventario, pedidos
from app.configuracion import configuracion


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
app.include_router(pedidos.enrutador)
app.include_router(inventario.enrutador)
app.include_router(administracion.enrutador)


@app.get("/salud")
def salud():
    return {"estado": "ok"}
