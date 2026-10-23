"""restricciones: movimientos sin venta, total y monto no negativos

Revision ID: ab1f2b63b89a
Revises: e0d0df2cd543
Create Date: 2026-10-22 22:10:31.909298

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab1f2b63b89a'
down_revision: Union[str, Sequence[str], None] = 'e0d0df2cd543'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TIPOS_CON_VENTA = "tipo IN ('reserva', 'liberacion', 'venta', 'ajuste_entrada', 'ajuste_salida')"
TIPOS_SIN_VENTA = "tipo IN ('reserva', 'ajuste_salida', 'liberacion', 'ajuste_entrada')"


def upgrade() -> None:
    # Un CHECK no se edita: se borra y se vuelve a crear con la nueva condición.
    op.drop_constraint("ck_movimientos_inventario_tipo", "movimientos_inventario", type_="check")
    op.create_check_constraint(
        "ck_movimientos_inventario_tipo", "movimientos_inventario", TIPOS_SIN_VENTA
    )
    op.create_check_constraint("ck_pedidos_total", "pedidos", "total >= 0")
    op.create_check_constraint("ck_pagos_monto", "pagos", "monto >= 0")


def downgrade() -> None:
    op.drop_constraint("ck_pagos_monto", "pagos", type_="check")
    op.drop_constraint("ck_pedidos_total", "pedidos", type_="check")
    op.drop_constraint("ck_movimientos_inventario_tipo", "movimientos_inventario", type_="check")
    op.create_check_constraint(
        "ck_movimientos_inventario_tipo", "movimientos_inventario", TIPOS_CON_VENTA
    )
