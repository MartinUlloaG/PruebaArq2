"""Rutas de inventario para operadores (y administradores)."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencias import obtener_sesion, requerir_rol
from app.infraestructura.repositorios import RepositorioInventario

enrutador = APIRouter(
    prefix="/inventario",
    tags=["inventario"],
    dependencies=[Depends(requerir_rol("operador", "administrador"))],
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


class FilaInventario(BaseModel):
    producto_id: int
    nombre: str
    cantidad: int
    precio: int = 0
    categoria: str = "Polerones"


class SolicitudAjusteInventario(BaseModel):
    producto_id: int = Field(gt=0)
    cantidad: int = Field(gt=0)
    tipo: str = Field(default="ajuste_entrada")  # "ajuste_entrada" o "ajuste_salida"


class SolicitudAjustePatch(BaseModel):
    cantidad: int | None = None
    ajuste: int | None = None
    tipo: str = "ajuste_entrada"


@enrutador.get("", response_model=list[FilaInventario])
def listar_inventario(sesion: Session = Depends(obtener_sesion)):
    # solo_activos=True: garantiza que ningún producto archivado o tecnológico desactivado aparezca
    filas = RepositorioInventario(sesion).listar_con_producto(solo_activos=True)
    return [
        FilaInventario(
            producto_id=p.id,
            nombre=p.nombre,
            cantidad=i.cantidad,
            precio=p.precio,
            categoria=_inferir_categoria(p.nombre),
        )
        for p, i in filas
    ]


@enrutador.patch("/{producto_id}", response_model=FilaInventario)
def ajustar_stock_patch(
    producto_id: int,
    solicitud: SolicitudAjustePatch,
    sesion: Session = Depends(obtener_sesion),
):
    repo = RepositorioInventario(sesion)
    cant = solicitud.cantidad if solicitud.cantidad is not None else solicitud.ajuste
    if cant is None or cant <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Debe especificar una cantidad o ajuste mayor a 0.",
        )
    tipo = solicitud.tipo or "ajuste_entrada"
    if tipo not in ("ajuste_entrada", "ajuste_salida"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tipo de ajuste inválido (use 'ajuste_entrada' o 'ajuste_salida').",
        )
    try:
        nuevo_stock = repo.ajustar_stock(
            producto_id=producto_id,
            cantidad=cant,
            tipo=tipo,
        )
        sesion.commit()
    except ValueError as e:
        sesion.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e

    filas = repo.listar_con_producto(solo_activos=False)
    for p, i in filas:
        if p.id == producto_id:
            return FilaInventario(
                producto_id=p.id,
                nombre=p.nombre,
                cantidad=nuevo_stock,
                precio=p.precio,
                categoria=_inferir_categoria(p.nombre),
            )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado.")


@enrutador.post("/ajuste", response_model=FilaInventario)
def ajustar_stock(
    solicitud: SolicitudAjusteInventario,
    sesion: Session = Depends(obtener_sesion),
):
    repo = RepositorioInventario(sesion)
    if solicitud.tipo not in ("ajuste_entrada", "ajuste_salida"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tipo de ajuste inválido (use 'ajuste_entrada' o 'ajuste_salida').",
        )
    try:
        nuevo_stock = repo.ajustar_stock(
            producto_id=solicitud.producto_id,
            cantidad=solicitud.cantidad,
            tipo=solicitud.tipo,
        )
        sesion.commit()
    except ValueError as e:
        sesion.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e

    filas = repo.listar_con_producto(solo_activos=False)
    for p, i in filas:
        if p.id == solicitud.producto_id:
            return FilaInventario(
                producto_id=p.id,
                nombre=p.nombre,
                cantidad=nuevo_stock,
                precio=p.precio,
                categoria=_inferir_categoria(p.nombre),
            )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado.")
