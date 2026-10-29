"""Recomendaciones: vienen de un servicio secundario que se puede caer.

Degradación controlada: si ese servicio no responde (o su Circuit Breaker está
abierto), se responde 200 con disponible=False y la lista vacía. El catálogo y la
compra no pasan por aquí, así que siguen funcionando igual.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.api.catalogo import ProductoCatalogo
from app.api.dependencias import obtener_recomendaciones, usuario_actual
from app.infraestructura.catalogo_documental import RepositorioCatalogo
from app.infraestructura.servicios_externos import ClienteRecomendaciones, ServicioNoDisponible

enrutador = APIRouter(
    prefix="/recomendaciones",
    tags=["recomendaciones"],
    dependencies=[Depends(usuario_actual)],
)


class Recomendaciones(BaseModel):
    disponible: bool
    productos: list[ProductoCatalogo]


@enrutador.get("", response_model=Recomendaciones)
def listar_recomendaciones(
    servicio: ClienteRecomendaciones = Depends(obtener_recomendaciones),
):
    try:
        ids = servicio.destacados()
    except ServicioNoDisponible:
        return Recomendaciones(disponible=False, productos=[])

    # El servicio solo conoce ids; nombre, precio y stock salen del catálogo propio.
    por_id = RepositorioCatalogo().por_id(ids)
    productos = [por_id[pid] for pid in ids if pid in por_id and por_id[pid]["disponibles"] > 0]
    return Recomendaciones(disponible=True, productos=productos)
