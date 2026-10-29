"""Compras del cliente: comprar (inicia la Saga) y ver sus pedidos."""

import hashlib
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.dependencias import UsuarioActual, obtener_sesion, requerir_rol
from app.dominio import compras
from app.infraestructura.modelos import Pedido
from app.infraestructura.repositorios import RepositorioIdempotencia, RepositorioPedidos

enrutador = APIRouter(prefix="/pedidos", tags=["pedidos"])
solo_clientes = requerir_rol("cliente")

# Cada falla prevista de la compra se traduce a un código HTTP.
CODIGOS_ERROR = {
    compras.ProductoNoDisponible: status.HTTP_404_NOT_FOUND,
    compras.StockInsuficiente: status.HTTP_409_CONFLICT,
}


class ItemSolicitud(BaseModel):
    producto_id: int = Field(gt=0)
    cantidad: int = Field(ge=1, le=compras.MAXIMO_POR_COMPRA)


class SolicitudCompra(BaseModel):
    """El carrito: uno o más productos distintos."""

    items: list[ItemSolicitud] = Field(min_length=1, max_length=20)

    @field_validator("items")
    @classmethod
    def sin_repetidos(cls, items: list[ItemSolicitud]) -> list[ItemSolicitud]:
        if len({i.producto_id for i in items}) != len(items):
            raise ValueError("Un producto aparece dos veces en el carrito.")
        return items


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


def _error(codigo: int, mensaje: str) -> JSONResponse:
    return JSONResponse({"detail": mensaje}, status_code=codigo)


@enrutador.post("", status_code=status.HTTP_202_ACCEPTED, response_model=PedidoRespuesta)
def comprar(
    solicitud: SolicitudCompra,
    clave: str = Header(alias="Idempotency-Key", min_length=1, max_length=100),
    usuario: UsuarioActual = Depends(solo_clientes),
    sesion: Session = Depends(obtener_sesion),
):
    """Reserva el stock y deja el pago en camino por Kafka. Responde 202: el pago se
    resuelve después, y la interfaz consulta GET /pedidos/{id} hasta ver el resultado.

    Receptor idempotente: la interfaz manda una clave nueva por cada compra. Si la
    misma solicitud llega dos veces (doble clic, reintento de red), la segunda recibe
    la respuesta guardada de la primera y no se vuelve a reservar ni a cobrar.
    """
    huella = hashlib.sha256(solicitud.model_dump_json().encode()).hexdigest()
    idempotencia = RepositorioIdempotencia(sesion)
    previa = idempotencia.tomar(usuario.id, clave, huella)
    sesion.commit()  # la clave queda tomada antes de empezar la Saga

    if previa is not None:
        if previa.huella != huella:
            return _error(422, "Esta clave de idempotencia ya se usó con otra compra.")
        if previa.codigo_respuesta is None:
            # La primera solicitud sigue en curso (o se cortó a la mitad). Ante la duda,
            # no se repite: repetir podría cobrar dos veces.
            return _error(409, "Esta compra ya se está procesando.")
        return JSONResponse(previa.cuerpo_respuesta, status_code=previa.codigo_respuesta)

    try:
        items = {i.producto_id: i.cantidad for i in solicitud.items}
        pedido = compras.iniciar_compra(sesion, usuario.id, items)
        codigo, cuerpo = status.HTTP_202_ACCEPTED, _a_respuesta(pedido).model_dump(mode="json")
    except compras.ErrorCompra as error:
        codigo, cuerpo = CODIGOS_ERROR[type(error)], {"detail": str(error)}

    idempotencia.guardar_respuesta(usuario.id, clave, codigo, cuerpo)
    sesion.commit()
    return JSONResponse(cuerpo, status_code=codigo)


@enrutador.get("", response_model=list[PedidoRespuesta])
def mis_pedidos(
    usuario: UsuarioActual = Depends(solo_clientes),
    sesion: Session = Depends(obtener_sesion),
):
    return [_a_respuesta(p) for p in RepositorioPedidos(sesion).listar_de_usuario(usuario.id)]


@enrutador.get("/{pedido_id}", response_model=PedidoRespuesta)
def ver_pedido(
    pedido_id: int,
    usuario: UsuarioActual = Depends(solo_clientes),
    sesion: Session = Depends(obtener_sesion),
):
    """Para seguir la Saga: stock_reservado (pago en proceso), pagado o fallido."""
    pedido = RepositorioPedidos(sesion).buscar_de_usuario(pedido_id, usuario.id)
    if pedido is None:  # tampoco se revela si existe un pedido de otro cliente
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontramos ese pedido.")
    return _a_respuesta(pedido)
