"""Compras del cliente: crear un pedido (reserva el stock) y ver sus pedidos."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencias import UsuarioActual, obtener_sesion, requerir_rol
from app.dominio import compras
from app.infraestructura.modelos import Pedido
from app.infraestructura.repositorios import RepositorioPedidos

enrutador = APIRouter(prefix="/pedidos", tags=["pedidos"])
solo_clientes = requerir_rol("cliente")


class SolicitudCompra(BaseModel):
    producto_id: int = Field(gt=0)
    cantidad: int = Field(ge=1, le=compras.MAXIMO_POR_COMPRA)


class ItemRespuesta(BaseModel):
    producto_id: int
    nombre: str
    cantidad: int
    precio_unitario: int


class PedidoRespuesta(BaseModel):
    pedido_id: int
    estado: str
    total: int
    creado_en: datetime
    items: list[ItemRespuesta]


def _a_respuesta(pedido: Pedido) -> PedidoRespuesta:
    return PedidoRespuesta(
        pedido_id=pedido.id,
        estado=pedido.estado,
        total=pedido.total,
        creado_en=pedido.creado_en,
        items=[
            ItemRespuesta(
                producto_id=item.producto_id,
                nombre=item.producto.nombre,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
            )
            for item in pedido.items
        ],
    )


@enrutador.post("", status_code=status.HTTP_201_CREATED, response_model=PedidoRespuesta)
def comprar(
    solicitud: SolicitudCompra,
    usuario: UsuarioActual = Depends(solo_clientes),
    sesion: Session = Depends(obtener_sesion),
):
    try:
        pedido = compras.reservar(sesion, usuario.id, solicitud.producto_id, solicitud.cantidad)
    except compras.ProductoNoDisponible as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except compras.StockInsuficiente as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    sesion.commit()
    return _a_respuesta(pedido)


@enrutador.get("", response_model=list[PedidoRespuesta])
def mis_pedidos(
    usuario: UsuarioActual = Depends(solo_clientes),
    sesion: Session = Depends(obtener_sesion),
):
    return [_a_respuesta(p) for p in RepositorioPedidos(sesion).listar_de_usuario(usuario.id)]
