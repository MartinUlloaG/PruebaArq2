"""Catálogo para cualquier usuario con sesión (el cliente compra desde aquí)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencias import obtener_sesion, usuario_actual
from app.infraestructura.repositorios import RepositorioInventario

enrutador = APIRouter(
    prefix="/catalogo",
    tags=["catálogo"],
    dependencies=[Depends(usuario_actual)],  # basta con tener sesión, sin importar el rol
)


def _inferir_categoria(nombre: str) -> str:
    n = nombre.lower()
    if any(k in n for k in ("hoodie", "polerón", "poleron", "crewneck", "sweater")):
        return "Polerones"
    if any(k in n for k in ("polera", "tee", "top", "manga larga")):
        return "Poleras"
    if any(k in n for k in ("calcetín", "calcetin", "calcetines", "sock")):
        return "Calcetines"
    if any(k in n for k in ("gorra", "beanie", "cap", "hat", "dad hat", "snapback")):
        return "Gorras"
    if any(k in n for k in ("pantalón", "pantalon", "cargo", "chino", "wide leg")):
        return "Pantalones"
    if any(k in n for k in ("blusa", "camisa", "túnica", "tunica")):
        return "Blusas"
    return "Polerones"


class ProductoCatalogo(BaseModel):
    producto_id: int
    nombre: str
    descripcion: str | None
    precio: int  # pesos chilenos, sin decimales
    disponibles: int
    categoria: str = "Polerones"


@enrutador.get("", response_model=list[ProductoCatalogo])
def listar_catalogo(sesion: Session = Depends(obtener_sesion)):
    # solo_activos=True: excluye productos eliminados o tecnológicos archivados
    filas = RepositorioInventario(sesion).listar_con_producto(solo_activos=True)
    return [
        ProductoCatalogo(
            producto_id=p.id,
            nombre=p.nombre,
            descripcion=p.descripcion,
            precio=p.precio,
            disponibles=i.cantidad,
            categoria=_inferir_categoria(p.nombre),
        )
        for p, i in filas
    ]
