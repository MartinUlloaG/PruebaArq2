"""Piezas 3 y 4: compra con reserva de stock, pago, idempotencia y compensación.

Pruebas de cierre: stock 1 y 100 compras simultáneas, exactamente 1 éxito; la misma
clave de idempotencia dos veces genera un solo cobro; si el pago falla, el stock vuelve.
Cada prueba crea su propio producto y lo borra al terminar: no gasta el stock de la demo.

La pasarela es la simulada de verdad (pasarelaSimulada/pasarela.py), corriendo dentro
de la prueba con TestClient en vez de en su propio puerto.
"""

import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.api.dependencias import obtener_pasarela
from app.configuracion import RAIZ
from app.dominio import compras
from app.infraestructura.base import Sesion
from app.infraestructura.circuit_breaker import CircuitBreaker
from app.infraestructura.modelos import (
    Inventario,
    ItemPedido,
    MovimientoInventario,
    Pago,
    Pedido,
    Producto,
    Usuario,
)
from app.infraestructura.repositorios import RepositorioInventario
from app.infraestructura.semilla import USUARIOS_DEMO, sembrar
from app.infraestructura.servicios_externos import ClientePasarela
from app.principal import app

sys.path.insert(0, str(RAIZ / "pasarelaSimulada"))
import pasarela as pasarela_simulada  # noqa: E402

cliente_http = TestClient(app)
CLAVES = {rol: (correo, clave) for correo, clave, rol in USUARIOS_DEMO}
PRECIO = 1000


@pytest.fixture(scope="module", autouse=True)
def datos_demo():
    sembrar()


@pytest.fixture(autouse=True)
def pasarela():
    """Pasarela simulada limpia en cada prueba, en modo "aprueba". Devuelve su cliente HTTP."""
    pasarela_simulada._respuestas.clear()
    pasarela_simulada._cobros.clear()
    pasarela_simulada._estado["modo"] = "aprueba"
    http = TestClient(pasarela_simulada.app)
    cliente = ClientePasarela(http, CircuitBreaker("pasarela de prueba"))
    app.dependency_overrides[obtener_pasarela] = lambda: cliente
    yield http
    app.dependency_overrides.pop(obtener_pasarela)


def _comprar(producto_id, cantidad, rol: str = "cliente", clave: str | None = None) -> httpx.Response:
    encabezados = {**_encabezado(rol), "Idempotency-Key": clave or uuid.uuid4().hex}
    return cliente_http.post(
        "/pedidos", json={"producto_id": producto_id, "cantidad": cantidad}, headers=encabezados
    )


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
            sesion.execute(delete(Pago).where(Pago.pedido_id.in_(pedido_ids)))
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


def _estado_pedido_y_pago(pedido_id: int) -> tuple[str, str | None]:
    with Sesion() as sesion:
        pago = sesion.scalar(select(Pago.estado).where(Pago.pedido_id == pedido_id))
        return sesion.get(Pedido, pedido_id).estado, pago


def _ultimo_pedido(producto_id: int) -> int:
    with Sesion() as sesion:
        return sesion.scalar(
            select(func.max(ItemPedido.pedido_id)).where(ItemPedido.producto_id == producto_id)
        )


def test_el_cliente_compra_paga_y_el_stock_baja(crear_producto, pasarela):
    producto_id = crear_producto(stock=3)
    respuesta = _comprar(producto_id, 2)
    pedido = respuesta.json()
    assert respuesta.status_code == 201
    assert pedido["estado"] == "pagado"
    assert pedido["total"] == 2 * PRECIO
    assert pedido["items"][0]["precio_unitario"] == PRECIO
    assert _stock_y_saldo(producto_id) == (1, 1)  # stock y auditoría cuadran
    assert _estado_pedido_y_pago(pedido["pedido_id"]) == ("pagado", "autorizado")
    assert pasarela.get("/cobros").json()["total"] == 1


def test_el_cliente_ve_su_pedido_guardado(crear_producto):
    producto_id = crear_producto(stock=1)
    creado = _comprar(producto_id, 1).json()
    mis_pedidos = cliente_http.get("/pedidos", headers=_encabezado("cliente")).json()
    assert creado["pedido_id"] in [p["pedido_id"] for p in mis_pedidos]


# --- Idempotencia (prueba de cierre de la pieza 4) -----------------------------


def test_la_misma_clave_dos_veces_genera_un_solo_cobro(crear_producto, pasarela):
    producto_id = crear_producto(stock=5)
    clave = uuid.uuid4().hex
    primera = _comprar(producto_id, 1, clave=clave)
    segunda = _comprar(producto_id, 1, clave=clave)  # doble clic o reintento de red

    assert primera.status_code == segunda.status_code == 201
    assert primera.json() == segunda.json()  # misma respuesta, mismo pedido
    assert pasarela.get("/cobros").json()["total"] == 1
    assert _stock_y_saldo(producto_id) == (4, 4)  # se reservó una sola vez
    assert _pedidos_del_producto(producto_id) == 1


def test_la_misma_clave_con_otra_compra_responde_422(crear_producto):
    producto_id = crear_producto(stock=5)
    clave = uuid.uuid4().hex
    assert _comprar(producto_id, 1, clave=clave).status_code == 201
    assert _comprar(producto_id, 2, clave=clave).status_code == 422
    assert _stock_y_saldo(producto_id) == (4, 4)


def test_sin_clave_de_idempotencia_responde_422(crear_producto):
    producto_id = crear_producto(stock=1)
    respuesta = cliente_http.post(
        "/pedidos", json={"producto_id": producto_id, "cantidad": 1}, headers=_encabezado("cliente")
    )
    assert respuesta.status_code == 422
    assert _stock_y_saldo(producto_id) == (1, 1)


# --- Compensación: si el pago falla, el stock vuelve ---------------------------


def test_pago_rechazado_responde_402_y_devuelve_el_stock(crear_producto, pasarela):
    producto_id = crear_producto(stock=3)
    pasarela.put("/simulacion", json={"modo": "rechaza"})

    respuesta = _comprar(producto_id, 2)

    assert respuesta.status_code == 402
    assert _stock_y_saldo(producto_id) == (3, 3)  # reserva (-2) + liberacion (+2)
    assert _estado_pedido_y_pago(_ultimo_pedido(producto_id)) == ("fallido", "rechazado")
    assert pasarela.get("/cobros").json()["total"] == 0


def test_pasarela_caida_responde_503_y_devuelve_el_stock(crear_producto, pasarela):
    producto_id = crear_producto(stock=3)
    pasarela.put("/simulacion", json={"modo": "falla"})

    respuesta = _comprar(producto_id, 1)

    assert respuesta.status_code == 503
    assert _stock_y_saldo(producto_id) == (3, 3)
    assert _estado_pedido_y_pago(_ultimo_pedido(producto_id)) == ("fallido", None)


def test_con_la_pasarela_lenta_el_circuito_se_abre_y_deja_de_esperar(crear_producto):
    """Tras 3 tiempos límite seguidos, el Circuit Breaker responde sin llamar a la pasarela."""
    producto_id = crear_producto(stock=10)
    llamadas = []

    def sin_respuesta(solicitud: httpx.Request) -> httpx.Response:
        llamadas.append(solicitud)
        raise httpx.ReadTimeout("la pasarela no respondió a tiempo", request=solicitud)

    http = httpx.Client(transport=httpx.MockTransport(sin_respuesta), base_url="http://pasarela")
    cliente = ClientePasarela(http, CircuitBreaker("pasarela lenta", umbral_fallas=3))
    app.dependency_overrides[obtener_pasarela] = lambda: cliente

    codigos = [_comprar(producto_id, 1).status_code for _ in range(5)]

    assert codigos == [503] * 5
    assert len(llamadas) == 3  # las compras 4 y 5 no esperaron a la pasarela
    assert cliente.circuito.estado == "abierto"
    assert _stock_y_saldo(producto_id) == (10, 10)  # las 5 reservas se devolvieron


# --- Reglas y validaciones --------------------------------------------------


def test_sin_stock_suficiente_responde_409_y_no_guarda_nada(crear_producto):
    producto_id = crear_producto(stock=1)
    respuesta = _comprar(producto_id, 2)
    assert respuesta.status_code == 409
    assert _stock_y_saldo(producto_id) == (1, 1)
    assert _pedidos_del_producto(producto_id) == 0  # el pedido se deshizo con la transacción


def test_producto_inexistente_responde_404():
    respuesta = _comprar(999_999, 1)
    assert respuesta.status_code == 404


@pytest.mark.parametrize("cantidad", [0, -1, compras.MAXIMO_POR_COMPRA + 1, "dos"])
def test_cantidad_invalida_responde_422(crear_producto, cantidad):
    producto_id = crear_producto(stock=50)
    respuesta = _comprar(producto_id, cantidad)
    assert respuesta.status_code == 422
    assert _stock_y_saldo(producto_id) == (50, 50)


@pytest.mark.parametrize("rol", ["operador", "administrador"])
def test_solo_el_cliente_puede_comprar(crear_producto, rol):
    producto_id = crear_producto(stock=1)
    respuesta = _comprar(producto_id, 1, rol=rol)
    assert respuesta.status_code == 403


def test_sin_sesion_no_se_puede_comprar():
    respuesta = cliente_http.post(
        "/pedidos", json={"producto_id": 1, "cantidad": 1}, headers={"Idempotency-Key": "x"}
    )
    assert respuesta.status_code == 401


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
