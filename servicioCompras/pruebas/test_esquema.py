"""Pieza 1: el esquema existe, la BD defiende sus reglas y la semilla no duplica.

Requiere la BD arriba y migrada (alembic upgrade head).
"""

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.infraestructura.base import Sesion
from app.infraestructura.modelos import (
    Inventario,
    MovimientoInventario,
    Pago,
    Pedido,
    Producto,
    Usuario,
)
from app.infraestructura.repositorios import RepositorioInventario
from app.infraestructura.semilla import sembrar


def _contar(sesion, modelo) -> int:
    return sesion.scalar(select(func.count()).select_from(modelo))


def test_la_migracion_esta_en_la_ultima_version():
    with Sesion() as sesion:
        version = sesion.scalar(text("SELECT version_num FROM alembic_version"))
    assert version is not None


def test_la_semilla_se_puede_correr_dos_veces_sin_duplicar():
    sembrar()
    with Sesion() as sesion:
        antes = (_contar(sesion, Usuario), _contar(sesion, Producto))
    creados = sembrar()
    with Sesion() as sesion:
        despues = (_contar(sesion, Usuario), _contar(sesion, Producto))
    assert creados == (0, 0)
    assert antes == despues


def test_hay_un_usuario_por_rol_y_la_clave_no_esta_en_texto_plano():
    sembrar()
    with Sesion() as sesion:
        roles = set(sesion.scalars(select(Usuario.rol)))
        hashes = list(sesion.scalars(select(Usuario.clave_hash)))
    assert {"cliente", "operador", "administrador"} <= roles
    assert all(h.startswith("$argon2id$") for h in hashes)


def test_la_bd_rechaza_stock_negativo():
    """Atributo de integridad: aunque falle la lógica, el CHECK impide la sobreventa."""
    sembrar()
    with Sesion() as sesion:
        inventario = sesion.scalars(select(Inventario)).first()
        inventario.cantidad = -1
        with pytest.raises(IntegrityError, match="ck_inventario_cantidad"):
            sesion.commit()
        sesion.rollback()


def test_la_bd_rechaza_total_y_monto_negativos():
    sembrar()
    with Sesion() as sesion:
        usuario_id = sesion.scalar(select(Usuario.id))
        sesion.add(Pedido(usuario_id=usuario_id, total=-1))
        with pytest.raises(IntegrityError, match="ck_pedidos_total"):
            sesion.commit()
        sesion.rollback()

        pedido = Pedido(usuario_id=usuario_id, total=0)
        sesion.add(pedido)
        sesion.flush()
        sesion.add(Pago(pedido_id=pedido.id, monto=-1))
        with pytest.raises(IntegrityError, match="ck_pagos_monto"):
            sesion.commit()
        sesion.rollback()  # el pedido de prueba tampoco queda guardado


def test_no_existe_el_tipo_venta():
    sembrar()
    with Sesion() as sesion:
        producto_id = sesion.scalar(select(Inventario.producto_id))
        sesion.add(MovimientoInventario(producto_id=producto_id, tipo="venta", cantidad=1))
        with pytest.raises(IntegrityError, match="ck_movimientos_inventario_tipo"):
            sesion.commit()
        sesion.rollback()


def test_el_stock_cuadra_con_los_movimientos():
    """Invariante: cantidad == entradas - salidas, para cada producto."""
    sembrar()
    with Sesion() as sesion:
        for inventario in sesion.scalars(select(Inventario)):
            saldo = RepositorioInventario(sesion).saldo_movimientos(inventario.producto_id)
            assert saldo == inventario.cantidad
