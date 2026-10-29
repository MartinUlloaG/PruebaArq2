"""Dos clientes compitiendo por el mismo producto: 100 compras al mismo tiempo (50 cada uno).

Para ver el detalle impreso:  python -m pytest pruebas/test_dos_clientes.py -s
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select

from ayudantes import pedidos_del_producto, stock_y_saldo
from app.dominio import compras
from app.infraestructura.base import Sesion
from app.infraestructura.modelos import Usuario

CLIENTES = ["cliente@demo.cl", "cliente01@demo.cl"]
INTENTOS = 100  # 50 por cliente


def _competir(producto_id: int) -> tuple[dict, float]:
    with Sesion() as sesion:
        ids = {c: sesion.scalar(select(Usuario.id).where(Usuario.correo == c)) for c in CLIENTES}
    turnos = [CLIENTES[i % 2] for i in range(INTENTOS)]  # se intercalan A, B, A, B...
    largada = threading.Barrier(INTENTOS)  # todas las compras parten en el mismo instante

    def intentar(correo: str) -> tuple[str, bool]:
        largada.wait()
        with Sesion() as sesion:
            try:
                # Solo el paso 1 de la Saga (la reserva): es lo que compite por el stock.
                compras.reservar(sesion, ids[correo], {producto_id: 1})
                sesion.commit()
                return correo, True
            except compras.StockInsuficiente:
                return correo, False

    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=INTENTOS) as ejecutor:
        resultados = list(ejecutor.map(intentar, turnos))
    demora = time.perf_counter() - inicio

    resumen = {c: {"aceptadas": 0, "rechazadas": 0} for c in CLIENTES}
    for correo, aceptada in resultados:
        resumen[correo]["aceptadas" if aceptada else "rechazadas"] += 1
    return resumen, demora


def _imprimir(titulo: str, stock_inicial: int, resumen: dict, demora: float, producto_id: int) -> None:
    stock, saldo = stock_y_saldo(producto_id)
    print(f"\n=== {titulo} ===")
    print(f"Stock inicial: {stock_inicial} | Intentos: {INTENTOS} (50 por cliente) | Tiempo: {demora:.2f} s")
    print(f"{'Cliente':<22}{'Aceptadas':>10}{'Rechazadas':>12}")
    for correo, r in resumen.items():
        print(f"{correo:<22}{r['aceptadas']:>10}{r['rechazadas']:>12}")
    total = sum(r["aceptadas"] for r in resumen.values())
    print(f"{'TOTAL':<22}{total:>10}{INTENTOS - total:>12}")
    print(f"Stock final: {stock} | Stock según movimientos: {saldo} | Pedidos creados: {pedidos_del_producto(producto_id)}")


@pytest.mark.parametrize("stock_inicial", [1, 30])
def test_dos_clientes_compiten_por_el_mismo_producto(crear_producto, stock_inicial):
    producto_id = crear_producto(stock=stock_inicial)

    resumen, demora = _competir(producto_id)
    _imprimir(f"Quedan {stock_inicial} unidad(es) y 2 clientes las quieren", stock_inicial, resumen, demora, producto_id)

    aceptadas = sum(r["aceptadas"] for r in resumen.values())
    assert aceptadas == stock_inicial  # se vende exactamente lo que había: ni más (sobreventa) ni menos
    assert stock_y_saldo(producto_id) == (0, 0)  # el stock cuadra con la auditoría
    assert pedidos_del_producto(producto_id) == stock_inicial
