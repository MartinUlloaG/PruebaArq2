"""Demostración para el informe y el video: por qué el stock se descuenta con UPDATE condicional.

Lanza 100 compras simultáneas de 1 unidad con tres estrategias:
  1. Leer y después escribir: leer el stock, validar en Python y escribir el nuevo valor.
  2. Versionado optimista (lo que proponía la Eva 1): escribir solo si el stock sigue
     igual al leído; si otro cambió la fila, la compra se rechaza.
  3. La del sistema: compras.reservar (UPDATE ... WHERE cantidad >= n).

Y en dos escenarios: stock 1 (la última unidad) y stock 50 (alcanza para la mitad).

Uso, desde servicioCompras (con la BD arriba):  python -m demostraciones.comparar_sobreventa
Crea productos temporales y los borra al terminar.
"""

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import delete, select, update

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

SOLICITUDES = 100
PAUSA = 0.01  # el trabajo que ocurre entre leer y escribir (validar, calcular el total...)


def _crear_producto(stock: int) -> int:
    with Sesion.begin() as sesion:
        producto = Producto(nombre=f"Demostración {uuid.uuid4().hex[:6]}", precio=1000)
        sesion.add(producto)
        sesion.flush()
        sesion.add(Inventario(producto_id=producto.id, cantidad=stock))
        sesion.add(MovimientoInventario(producto_id=producto.id, tipo="ajuste_entrada", cantidad=stock))
        return producto.id


def _borrar_producto(producto_id: int) -> int:
    """Borra lo creado y devuelve el stock con que quedó."""
    with Sesion.begin() as sesion:
        stock = sesion.get(Inventario, producto_id).cantidad
        pedidos = list(sesion.scalars(select(ItemPedido.pedido_id).where(ItemPedido.producto_id == producto_id)))
        sesion.execute(delete(MovimientoInventario).where(MovimientoInventario.producto_id == producto_id))
        sesion.execute(delete(ItemPedido).where(ItemPedido.pedido_id.in_(pedidos)))
        sesion.execute(delete(Pedido).where(Pedido.id.in_(pedidos)))
        sesion.execute(delete(Inventario).where(Inventario.producto_id == producto_id))
        sesion.execute(delete(Producto).where(Producto.id == producto_id))
        return stock


def _stock_actual(sesion, producto_id: int) -> int:
    return sesion.scalar(select(Inventario.cantidad).where(Inventario.producto_id == producto_id))


def compra_leer_y_escribir(producto_id: int, usuario_id: int) -> bool:
    with Sesion() as sesion:
        leido = _stock_actual(sesion, producto_id)
        if leido < 1:
            return False
        time.sleep(PAUSA)
        sesion.get(Inventario, producto_id).cantidad = leido - 1
        sesion.commit()
        return True


def compra_optimista(producto_id: int, usuario_id: int) -> bool:
    with Sesion() as sesion:
        leido = _stock_actual(sesion, producto_id)
        if leido < 1:
            return False
        time.sleep(PAUSA)
        # El valor leído hace de versión: si cambió, otro compró antes y se rechaza.
        resultado = sesion.execute(
            update(Inventario)
            .where(Inventario.producto_id == producto_id, Inventario.cantidad == leido)
            .values(cantidad=leido - 1)
        )
        sesion.commit()
        return resultado.rowcount == 1


def compra_del_sistema(producto_id: int, usuario_id: int) -> bool:
    with Sesion() as sesion:
        try:
            compras.reservar(sesion, usuario_id, {producto_id: 1})
            sesion.commit()
            return True
        except compras.StockInsuficiente:
            return False


def medir(nombre: str, comprar, stock_inicial: int) -> None:
    with Sesion() as sesion:
        usuario_id = sesion.scalar(select(Usuario.id).where(Usuario.rol == "cliente"))
    producto_id = _crear_producto(stock_inicial)
    largada = threading.Barrier(SOLICITUDES)  # todas las compras parten a la vez

    def una_compra(_) -> bool:
        largada.wait()
        return comprar(producto_id, usuario_id)

    with ThreadPoolExecutor(max_workers=SOLICITUDES) as ejecutor:
        aceptadas = list(ejecutor.map(una_compra, range(SOLICITUDES))).count(True)
    stock_final = _borrar_producto(producto_id)

    vendidas_de_mas = max(aceptadas - stock_inicial, 0)
    rechazadas_con_stock = min(SOLICITUDES, stock_inicial) - aceptadas if aceptadas < stock_inicial else 0
    cuadra = "sí" if aceptadas + stock_final == stock_inicial else "NO"
    print(
        f"  {nombre:<28} aceptadas: {aceptadas:>3}   stock final: {stock_final:>3}   "
        f"cuadra: {cuadra:<2}   vendidas de más: {vendidas_de_mas:>3}   "
        f"rechazadas habiendo stock: {rechazadas_con_stock:>3}"
    )


ESTRATEGIAS = [
    ("Leer y después escribir", compra_leer_y_escribir),
    ("Versionado optimista", compra_optimista),
    ("UPDATE condicional (sistema)", compra_del_sistema),
]

if __name__ == "__main__":
    for stock in (1, 50):
        print(f"\n{SOLICITUDES} compras simultáneas de 1 unidad, stock inicial {stock}:")
        for nombre, estrategia in ESTRATEGIAS:
            medir(nombre, estrategia, stock)
