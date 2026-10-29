"""Catálogo para cualquier usuario con sesión (el cliente compra desde aquí).

Se lee desde MongoDB, el modelo de lectura (ver infraestructura/catalogo_documental.py).
La categoría y los atributos vienen del documento de cada prenda, no se adivinan.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from pymongo.errors import PyMongoError

from app.api.dependencias import usuario_actual
from app.infraestructura.catalogo_documental import RepositorioCatalogo

enrutador = APIRouter(
    prefix="/catalogo",
    tags=["catálogo"],
    dependencies=[Depends(usuario_actual)],
)


class ProductoCatalogo(BaseModel):
    producto_id: int
    nombre: str
    descripcion: str | None
    categoria: str
    precio: int  # pesos chilenos, sin decimales
    disponibles: int
    atributos: dict = {}  # tallas, colores, material... cambian según la prenda


class Categoria(BaseModel):
    nombre: str
    productos: int
    unidades: int


def _sin_catalogo(error: Exception) -> HTTPException:
    return HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE, "El catálogo no está disponible en este momento."
    )


@enrutador.get("", response_model=list[ProductoCatalogo])
def listar_catalogo(categoria: str | None = None):
    try:
        return RepositorioCatalogo().listar(categoria)
    except PyMongoError as error:
        raise _sin_catalogo(error) from error


@enrutador.get("/categorias", response_model=list[Categoria])
def listar_categorias():
    try:
        return RepositorioCatalogo().categorias()
    except PyMongoError as error:
        raise _sin_catalogo(error) from error
