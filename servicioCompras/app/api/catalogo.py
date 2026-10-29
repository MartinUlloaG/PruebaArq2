"""Catálogo para cualquier usuario con sesión (el cliente compra desde aquí)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencias import obtener_sesion, usuario_actual
from app.infraestructura.repositorios import RepositorioInventario

enrutador = APIRouter(
    prefix="/catalogo",
    tags=["catálogo"],
    dependencies=[Depends(usuario_actual)],  
)


class ProductoCatalogo(BaseModel):
    producto_id: int
    nombre: str
    descripcion: str | None
    precio: int  
    disponibles: int


@enrutador.get("", response_model=list[ProductoCatalogo])
def listar_catalogo(sesion: Session = Depends(obtener_sesion)):
    filas = RepositorioInventario(sesion).listar_con_producto(solo_activos=True)
    return [
        ProductoCatalogo(
            producto_id=p.id,
            nombre=p.nombre,
            descripcion=p.descripcion,
            precio=p.precio,
            disponibles=i.cantidad,
        )
        for p, i in filas
    ]
