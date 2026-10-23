"""Demostración para el informe y el video: por qué el stock se descuenta con UPDATE condicional.

Lanza 100 compras simultáneas de la última unidad de un producto con dos estrategias:
  1. Ingenua: leer el stock, validar en Python y después escribir el nuevo valor.
  2. La del sistema: compras.reservar (UPDATE ... WHERE cantidad >= n).

Uso, desde servicioCompras (con la BD arriba):  python -m demostraciones.comparar_sobreventa
Crea productos temporales y los borra al terminar.
"""

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

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

SOLICITUDES = 100


def _crear_producto_con_una_unidad() -> int:
    with Sesion.begin() as sesion:
        producto = Producto(nombre=f"Demostración {uuid.uuid4().hex[:6]}", precio=1000)
        sesion.add(producto)
        sesion.flush()
        sesion.add(Inventario(producto_id=producto.id, cantidad=1))
        sesion.add(MovimientoInventario(producto_id=producto.id, tipo="ajuste_entrada", cantidad=1))
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


def compra_ingenua(producto_id: int, usuario_id: int) -> bool:
    with Sesion() as sesion:
        stock_leido = sesion.scalar(select(Inventario.cantidad).where(Inventario.producto_id == producto_id))
        if stock_leido < 1:
            return False
        time.sleep(0.01)  # el trabajo que ocurre entre leer y escribir (validar, calcular el total...)
        sesion.get(Inventario, producto_id).cantidad = stock_leido - 1
        sesion.commit()
        return True


def compra_del_sistema(producto_id: int, usuario_id: int) -> bool:
    with Sesion() as sesion:
        try:
            compras.reservar(sesion, usuario_id, producto_id, 1)
            sesion.commit()
            return True
        except compras.StockInsuficiente:
            return False


def medir(nombre: str, comprar) -> None:
    with Sesion() as sesion:
        usuario_id = sesion.scalar(select(Usuario.id).where(Usuario.rol == "cliente"))
    producto_id = _crear_producto_con_una_unidad()
    largada = threading.Barrier(SOLICITUDES)  # todas las compras parten a la vez

    def una_compra(_) -> bool:
        largada.wait()
        return comprar(producto_id, usuario_id)

    with ThreadPoolExecutor(max_workers=SOLICITUDES) as ejecutor:
        exitos = list(ejecutor.map(una_compra, range(SOLICITUDES))).count(True)
    stock_final = _borrar_producto(producto_id)
    print(f"{nombre:<32} compras aceptadas: {exitos:>3}   stock final: {stock_final}")


if __name__ == "__main__":
    print(f"{SOLICITUDES} compras simultáneas de un producto con stock 1:\n")
    medir("Leer y después escribir", compra_ingenua)
    medir("UPDATE condicional (sistema)", compra_del_sistema)
