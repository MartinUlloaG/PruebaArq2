"""bloqueo del login y transacción de la pasarela

Revision ID: c7a2d9e41b05
Revises: 543b7fbfc5e3
Create Date: 2026-10-29 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c7a2d9e41b05'
down_revision: Union[str, Sequence[str], None] = '543b7fbfc5e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('usuarios', sa.Column('intentos_fallidos', sa.Integer(), server_default='0', nullable=False))
    op.add_column('usuarios', sa.Column('bloqueado_hasta', sa.DateTime(timezone=True), nullable=True))
    op.add_column('pagos', sa.Column('token_pasarela', sa.String(length=64), nullable=True))
    op.add_column('pagos', sa.Column('url_pago', sa.String(length=300), nullable=True))
    op.add_column('pagos', sa.Column('medio', sa.String(length=60), nullable=True))
    op.add_column('pagos', sa.Column('motivo', sa.String(length=200), nullable=True))
    op.add_column('pagos', sa.Column('confirmacion_pedida_en', sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint(op.f('uq_pagos_token_pasarela'), 'pagos', ['token_pasarela'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f('uq_pagos_token_pasarela'), 'pagos', type_='unique')
    op.drop_column('pagos', 'confirmacion_pedida_en')
    op.drop_column('pagos', 'motivo')
    op.drop_column('pagos', 'medio')
    op.drop_column('pagos', 'url_pago')
    op.drop_column('pagos', 'token_pasarela')
    op.drop_column('usuarios', 'bloqueado_hasta')
    op.drop_column('usuarios', 'intentos_fallidos')
