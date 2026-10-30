
import hashlib
import threading
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.dependencias import UsuarioActual, obtener_sesion, requerir_rol
from app.configuracion import configuracion
from app.dominio import compras
from app.infraestructura.modelos import Pedido
from app.infraestructura.repositorios import RepositorioIdempotencia, RepositorioPedidos

enrutador = APIRouter(prefix="/pedidos", tags=["pedidos"])
solo_clientes = requerir_rol("cliente")
cupos_de_compra = threading.BoundedSemaphore(configuracion.compras_simultaneas)

CODIGOS_ERROR = {
    compras.ProductoNoDisponible: status.HTTP_404_NOT_FOUND,
    compras.StockInsuficiente: status.HTTP_409_CONFLICT,
    compras.PagoNoEncontrado: status.HTTP_404_NOT_FOUND,
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


class PagoRespuesta(BaseModel):
    """Lo que el cliente ve de su pago. url_pago: dónde paga mientras la reserva siga viva."""

    estado: str
    url_pago: str | None
    medio: str | None
    motivo: str | None


class PedidoRespuesta(BaseModel):
    pedido_id: int
    estado: str
    total: int
    creado_en: datetime
    items: list[ItemRespuesta]
    pago: PagoRespuesta | None


class VueltaDePasarela(BaseModel):
    token: str = Field(min_length=1, max_length=64)


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
        pago=PagoRespuesta(
            estado=pedido.pago.estado,
            url_pago=pedido.pago.url_pago if pedido.estado == "stock_reservado" else None,
            medio=pedido.pago.medio,
            motivo=pedido.pago.motivo,
        )
        if pedido.pago
        else None,
    )


def _soltar_conexion(sesion: Session) -> None:
    """Termina la transacción de lectura y devuelve la conexión al pool altiro.

    Si no, la conexión queda "idle in transaction" hasta que FastAPI cierra la sesión, y
    ese cierre hace fila en el mismo grupo de hilos que las peticiones. Con mucha carga
    (la interfaz consultando el pedido cada segundo) las conexiones quedaban retenidas sin
    hacer nada, se agotaba el pool y salían errores 500.
    """
    sesion.rollback()


def _error(codigo: int, mensaje: str, encabezados: dict | None = None) -> JSONResponse:
    return JSONResponse({"detail": mensaje}, status_code=codigo, headers=encabezados)


@enrutador.post("", status_code=status.HTTP_202_ACCEPTED, response_model=PedidoRespuesta)
def comprar(
    solicitud: SolicitudCompra,
    clave: str = Header(alias="Idempotency-Key", min_length=1, max_length=100),
    usuario: UsuarioActual = Depends(solo_clientes),
    sesion: Session = Depends(obtener_sesion),
):
    """Reserva el stock y deja el pago en camino por Kafka. Responde 202: el pago se
    resuelve después. La interfaz consulta GET /pedidos/{id} hasta que aparece la URL de
    la pasarela y manda al comprador ahí.

    Receptor idempotente: la interfaz manda una clave nueva por cada compra. Si la
    misma solicitud llega dos veces (doble clic, reintento de red), la segunda recibe
    la respuesta guardada de la primera y no se vuelve a reservar ni a cobrar.

    Con mucha demanda responde 503 con Retry-After. Eso pasa ANTES de tomar la clave de
    idempotencia, así que reintentar con la misma clave es seguro.
    """
    if not cupos_de_compra.acquire(timeout=configuracion.segundos_espera_compra):
        return _error(503, "Hay mucha demanda en este momento. Intenta de nuevo en unos segundos.", {"Retry-After": "2"})
    try:
        return _comprar(solicitud, clave, usuario, sesion)
    finally:
        cupos_de_compra.release()


def _comprar(solicitud: SolicitudCompra, clave: str, usuario: UsuarioActual, sesion: Session) -> JSONResponse:
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


@enrutador.post("/confirmar-pago", status_code=status.HTTP_202_ACCEPTED, response_model=PedidoRespuesta)
def confirmar_pago(
    vuelta: VueltaDePasarela,
    usuario: UsuarioActual = Depends(solo_clientes),
    sesion: Session = Depends(obtener_sesion),
):
    """El comprador volvió de la pasarela con su token. Deja la confirmación en camino por
    Kafka (el cobro lo hace el servicio de pagos). Se puede repetir sin cobrar dos veces.
    Solo sirve el token de un pedido propio: con uno ajeno responde 404."""
    try:
        pedido = compras.pedir_confirmacion(sesion, usuario.id, vuelta.token)
        return _a_respuesta(pedido)
    except compras.ErrorCompra as error:
        raise HTTPException(CODIGOS_ERROR[type(error)], str(error)) from error
    finally:
        _soltar_conexion(sesion)


@enrutador.get("", response_model=list[PedidoRespuesta])
def mis_pedidos(
    usuario: UsuarioActual = Depends(solo_clientes),
    sesion: Session = Depends(obtener_sesion),
):
    try:
        return [_a_respuesta(p) for p in RepositorioPedidos(sesion).listar_de_usuario(usuario.id)]
    finally:
        _soltar_conexion(sesion)


@enrutador.get("/{pedido_id}", response_model=PedidoRespuesta)
def ver_pedido(
    pedido_id: int,
    usuario: UsuarioActual = Depends(solo_clientes),
    sesion: Session = Depends(obtener_sesion),
):
    """Para seguir la Saga: stock_reservado (pago en proceso), pagado o fallido."""
    try:
        pedido = RepositorioPedidos(sesion).buscar_de_usuario(pedido_id, usuario.id)
        if pedido is None:  # tampoco se revela si existe un pedido de otro cliente
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontramos ese pedido.")
        return _a_respuesta(pedido)
    finally:
        _soltar_conexion(sesion)
