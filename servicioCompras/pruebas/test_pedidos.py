"""Pieza 3: compra con reserva de stock y control de concurrencia.

Prueba de cierre: stock 1 y 100 compras simultáneas, exactamente 1 éxito.
Cada prueba crea su propio producto y lo borra al terminar: no gasta el stock de la demo.
"""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.dominio import compras
from app.infraestructura.base import Sesion
from app.infraestructura.modelos import (
    Inventario,
    ItemPedido,
    MovimientoInventario,
    Pedido,
    Producto,
    Usuario,
)
from app.infraestructura.repositorios import RepositorioInventario
from app.infraestructura.semilla import USUARIOS_DEMO, sembrar
from app.principal import app

cliente_http = TestClient(app)
CLAVES = {rol: (correo, clave) for correo, clave, rol in USUARIOS_DEMO}
PRECIO = 1000


@pytest.fixture(scope="module", autouse=True)
def datos_demo():
    sembrar()


def _encabezado(rol: str) -> dict:
    correo, clave = CLAVES[rol]
    respuesta = cliente_http.post("/autenticacion/ingresar", json={"correo": correo, "clave": clave})
    return {"Authorization": f"Bearer {respuesta.json()['token_acceso']}"}


@pytest.fixture
def crear_producto():
    """Fábrica: crea un producto con stock (y su movimiento de entrada) y lo borra al final."""
    creados = []

    def crear(stock: int) -> int:
        with Sesion.begin() as sesion:
            producto = Producto(nombre=f"Prueba {uuid.uuid4().hex[:8]}", precio=PRECIO)
            sesion.add(producto)
            sesion.flush()
            sesion.add(Inventario(producto_id=producto.id, cantidad=stock))
            sesion.add(
                MovimientoInventario(producto_id=producto.id, tipo="ajuste_entrada", cantidad=stock)
            )
        creados.append(producto.id)
        return producto.id

    yield crear

    with Sesion.begin() as sesion:
        for producto_id in creados:
            pedidos = select(ItemPedido.pedido_id).where(ItemPedido.producto_id == producto_id)
            pedido_ids = list(sesion.scalars(pedidos))
            sesion.execute(delete(MovimientoInventario).where(MovimientoInventario.producto_id == producto_id))
            sesion.execute(delete(ItemPedido).where(ItemPedido.pedido_id.in_(pedido_ids)))
            sesion.execute(delete(Pedido).where(Pedido.id.in_(pedido_ids)))
            sesion.execute(delete(Inventario).where(Inventario.producto_id == producto_id))
            sesion.execute(delete(Producto).where(Producto.id == producto_id))


def _stock_y_saldo(producto_id: int) -> tuple[int, int]:
    with Sesion() as sesion:
        stock = sesion.get(Inventario, producto_id).cantidad
        return stock, RepositorioInventario(sesion).saldo_movimientos(producto_id)


def _pedidos_del_producto(producto_id: int) -> int:
    with Sesion() as sesion:
        return len(list(sesion.scalars(select(ItemPedido.id).where(ItemPedido.producto_id == producto_id))))


# --- Flujo normal -----------------------------------------------------------


def test_el_cliente_compra_y_el_stock_baja(crear_producto):
    producto_id = crear_producto(stock=3)
    respuesta = cliente_http.post(
        "/pedidos", json={"producto_id": producto_id, "cantidad": 2}, headers=_encabezado("cliente")
    )
    pedido = respuesta.json()
    assert respuesta.status_code == 201
    assert pedido["estado"] == "stock_reservado"
    assert pedido["total"] == 2 * PRECIO
    assert pedido["items"][0]["precio_unitario"] == PRECIO
    assert _stock_y_saldo(producto_id) == (1, 1)  # stock y auditoría cuadran


def test_el_cliente_ve_su_pedido_guardado(crear_producto):
    producto_id = crear_producto(stock=1)
    encabezado = _encabezado("cliente")
    creado = cliente_http.post(
        "/pedidos", json={"producto_id": producto_id, "cantidad": 1}, headers=encabezado
    ).json()
    mis_pedidos = cliente_http.get("/pedidos", headers=encabezado).json()
    assert creado["pedido_id"] in [p["pedido_id"] for p in mis_pedidos]


# --- Reglas y validaciones --------------------------------------------------


def test_sin_stock_suficiente_responde_409_y_no_guarda_nada(crear_producto):
    producto_id = crear_producto(stock=1)
    respuesta = cliente_http.post(
        "/pedidos", json={"producto_id": producto_id, "cantidad": 2}, headers=_encabezado("cliente")
    )
    assert respuesta.status_code == 409
    assert _stock_y_saldo(producto_id) == (1, 1)
    assert _pedidos_del_producto(producto_id) == 0  # el pedido se deshizo con la transacción


def test_producto_inexistente_responde_404():
    respuesta = cliente_http.post(
        "/pedidos", json={"producto_id": 999_999, "cantidad": 1}, headers=_encabezado("cliente")
    )
    assert respuesta.status_code == 404


@pytest.mark.parametrize("cantidad", [0, -1, compras.MAXIMO_POR_COMPRA + 1, "dos"])
def test_cantidad_invalida_responde_422(crear_producto, cantidad):
    producto_id = crear_producto(stock=50)
    respuesta = cliente_http.post(
        "/pedidos", json={"producto_id": producto_id, "cantidad": cantidad}, headers=_encabezado("cliente")
    )
    assert respuesta.status_code == 422
    assert _stock_y_saldo(producto_id) == (50, 50)


@pytest.mark.parametrize("rol", ["operador", "administrador"])
def test_solo_el_cliente_puede_comprar(crear_producto, rol):
    producto_id = crear_producto(stock=1)
    respuesta = cliente_http.post(
        "/pedidos", json={"producto_id": producto_id, "cantidad": 1}, headers=_encabezado(rol)
    )
    assert respuesta.status_code == 403


def test_sin_sesion_no_se_puede_comprar():
    assert cliente_http.post("/pedidos", json={"producto_id": 1, "cantidad": 1}).status_code == 401


# --- Concurrencia (prueba de cierre) ------------------------------------------


def test_100_compras_simultaneas_de_la_ultima_unidad_dan_un_solo_exito(crear_producto):
    producto_id = crear_producto(stock=1)
    with Sesion() as sesion:
        usuario_id = sesion.scalar(select(Usuario.id).where(Usuario.rol == "cliente"))

    solicitudes = 100
    largada = threading.Barrier(solicitudes)  # todas parten a la vez

    def comprar() -> bool:
        largada.wait()
        with Sesion() as sesion:
            try:
                compras.reservar(sesion, usuario_id, producto_id, 1)
                sesion.commit()
                return True
            except compras.StockInsuficiente:
                return False

    with ThreadPoolExecutor(max_workers=solicitudes) as ejecutor:
        resultados = list(ejecutor.map(lambda _: comprar(), range(solicitudes)))

    assert resultados.count(True) == 1
    assert resultados.count(False) == solicitudes - 1
    assert _stock_y_saldo(producto_id) == (0, 0)
    assert _pedidos_del_producto(producto_id) == 1
