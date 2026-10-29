"""Funciones comunes de las pruebas de compra."""

import sys
import uuid

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.configuracion import RAIZ
from app.infraestructura.base import Sesion
from app.infraestructura.modelos import Inventario, ItemPedido, Outbox, Pago, Pedido
from app.infraestructura.repositorios import RepositorioInventario
from app.infraestructura.semilla import USUARIOS_DEMO
from app.principal import app

# Los otros servicios viven en sus carpetas; se importan para probarlos dentro del mismo proceso.
sys.path.insert(0, str(RAIZ / "pasarelaSimulada"))
sys.path.insert(0, str(RAIZ / "servicioPagos"))

# Sin "with": no corre el ciclo de vida de la app, o sea, no arranca los hilos de Kafka.
cliente_http = TestClient(app)
CLAVES = {rol: (correo, clave) for correo, clave, rol in USUARIOS_DEMO}
PRECIO = 1000


def encabezado(rol: str) -> dict:
    correo, clave = CLAVES[rol]
    respuesta = cliente_http.post("/autenticacion/ingresar", json={"correo": correo, "clave": clave})
    return {"Authorization": f"Bearer {respuesta.json()['token_acceso']}"}


def comprar(producto_id, cantidad, rol: str = "cliente", clave: str | None = None) -> httpx.Response:
    encabezados = {**encabezado(rol), "Idempotency-Key": clave or uuid.uuid4().hex}
    return cliente_http.post(
        "/pedidos", json={"items": [{"producto_id": producto_id, "cantidad": cantidad}]}, headers=encabezados
    )


def stock_y_saldo(producto_id: int) -> tuple[int, int]:
    """(stock actual, stock reconstruido desde los movimientos): deben ser iguales."""
    with Sesion() as sesion:
        stock = sesion.get(Inventario, producto_id).cantidad
        return stock, RepositorioInventario(sesion).saldo_movimientos(producto_id)


def pedidos_del_producto(producto_id: int) -> int:
    with Sesion() as sesion:
        return sesion.scalar(
            select(func.count()).select_from(ItemPedido).where(ItemPedido.producto_id == producto_id)
        )


def estado_pedido_y_pago(pedido_id: int) -> tuple[str, str | None]:
    with Sesion() as sesion:
        pago = sesion.scalar(select(Pago.estado).where(Pago.pedido_id == pedido_id))
        return sesion.get(Pedido, pedido_id).estado, pago


def mensajes_outbox(pedido_id: int, topico: str) -> list[dict]:
    with Sesion() as sesion:
        consulta = select(Outbox.contenido).where(Outbox.clave == str(pedido_id), Outbox.topico == topico)
        return list(sesion.scalars(consulta))
