from fastapi import FastAPI

from app.api import administracion, autenticacion, inventario

app = FastAPI(title="Servicio de compras")

app.include_router(autenticacion.enrutador)
app.include_router(inventario.enrutador)
app.include_router(administracion.enrutador)


@app.get("/salud")
def salud():
    return {"estado": "ok"}
