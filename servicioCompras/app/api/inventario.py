"""Rutas de inventario para operadores (y administradores)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencias import obtener_sesion, requerir_rol
from app.infraestructura.repositorios import RepositorioInventario

enrutador = APIRouter(
    prefix="/inventario",
    tags=["inventario"],
    dependencies=[Depends(requerir_rol("operador", "administrador"))],
)


class FilaInventario(BaseModel):
    producto_id: int
    nombre: str
    cantidad: int


@enrutador.get("", response_model=list[FilaInventario])
def listar_inventario(sesion: Session = Depends(obtener_sesion)):
    filas = RepositorioInventario(sesion).listar_con_producto()
    return [
        FilaInventario(producto_id=p.id, nombre=p.nombre, cantidad=i.cantidad) for p, i in filas
    ]
