"""Recomendaciones: vienen de un servicio secundario que se puede caer.

Degradación controlada: si ese servicio no responde (o su Circuit Breaker está
abierto), se responde 200 con disponible=False y la lista vacía. El catálogo y la
compra no pasan por aquí, así que siguen funcionando igual.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.catalogo import ProductoCatalogo
from app.api.dependencias import obtener_recomendaciones, obtener_sesion, usuario_actual
from app.infraestructura.repositorios import RepositorioInventario
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
    sesion: Session = Depends(obtener_sesion),
    servicio: ClienteRecomendaciones = Depends(obtener_recomendaciones),
):
    try:
        ids = servicio.destacados()
    except ServicioNoDisponible:
        return Recomendaciones(disponible=False, productos=[])

    # El servicio solo conoce ids; nombre, precio y stock salen del catálogo propio.
    filas = {p.id: (p, i) for p, i in RepositorioInventario(sesion).listar_con_producto(solo_activos=True)}
    productos = [
        ProductoCatalogo(
            producto_id=p.id,
            nombre=p.nombre,
            descripcion=p.descripcion,
            precio=p.precio,
            disponibles=i.cantidad,
        )
        for p, i in (filas[pid] for pid in ids if pid in filas)
        if i.cantidad > 0
    ]
    return Recomendaciones(disponible=True, productos=productos)
