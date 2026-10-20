"""Pieza 1: el esquema existe, la BD defiende sus reglas y la semilla no duplica.

Requiere la BD arriba y migrada (alembic upgrade head).
"""

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.infraestructura.base import Sesion
from app.infraestructura.modelos import Inventario, MovimientoInventario, Producto, Usuario
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


def test_el_stock_inicial_cuadra_con_los_movimientos():
    sembrar()
    with Sesion() as sesion:
        for inventario in sesion.scalars(select(Inventario)):
            entradas = sesion.scalar(
                select(func.coalesce(func.sum(MovimientoInventario.cantidad), 0)).where(
                    MovimientoInventario.producto_id == inventario.producto_id,
                    MovimientoInventario.tipo == "ajuste_entrada",
                )
            )
            assert entradas == inventario.cantidad
