"""Rutas de inventario para operadores (y administradores).

El stock se lee y se ajusta en Postgres (la verdad). La categoría se toma del documento
de la prenda en Mongo, solo para mostrarla.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from pymongo.errors import PyMongoError
from sqlalchemy.orm import Session

from app.api.dependencias import obtener_sesion, requerir_rol
from app.infraestructura.catalogo_documental import RepositorioCatalogo
from app.infraestructura.repositorios import RepositorioInventario

enrutador = APIRouter(
    prefix="/inventario",
    tags=["inventario"],
    dependencies=[Depends(requerir_rol("operador", "administrador"))],
)


class FilaInventario(BaseModel):
    producto_id: int
    nombre: str
    categoria: str | None
    precio: int
    cantidad: int


class SolicitudAjuste(BaseModel):
    cantidad: int = Field(gt=0, le=1000)
    tipo: Literal["ajuste_entrada", "ajuste_salida"]


def _categorias(ids: list[int]) -> dict[int, str]:
    try:
        return {pid: p["categoria"] for pid, p in RepositorioCatalogo().por_id(ids).items()}
    except PyMongoError:
        return {}  # sin Mongo igual se puede trabajar el stock; solo falta la categoría


def _filas(sesion: Session, producto_id: int | None = None) -> list[FilaInventario]:
    filas = RepositorioInventario(sesion).listar_con_producto(solo_activos=True)
    if producto_id is not None:
        filas = [(p, i) for p, i in filas if p.id == producto_id]
    categorias = _categorias([p.id for p, _ in filas])
    return [
        FilaInventario(
            producto_id=p.id,
            nombre=p.nombre,
            categoria=categorias.get(p.id),
            precio=p.precio,
            cantidad=i.cantidad,
        )
        for p, i in filas
    ]


@enrutador.get("", response_model=list[FilaInventario])
def listar_inventario(sesion: Session = Depends(obtener_sesion)):
    return _filas(sesion)


@enrutador.patch("/{producto_id}", response_model=FilaInventario)
def ajustar_stock(
    producto_id: int,
    solicitud: SolicitudAjuste,
    sesion: Session = Depends(obtener_sesion),
):
    """Recepción (+) o merma (-). Queda en movimientos_inventario y sale por Kafka a Mongo."""
    try:
        RepositorioInventario(sesion).ajustar_stock(producto_id, solicitud.cantidad, solicitud.tipo)
        sesion.commit()
    except ValueError as error:
        sesion.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    filas = _filas(sesion, producto_id)
    if not filas:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado.")
    return filas[0]
