from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infraestructura.base import Base

# Los CHECK llevan nombre corto; base.py le antepone "ck_<tabla>_".
ROLES = ("cliente", "operador", "administrador")
ESTADOS_PEDIDO = ("pendiente", "stock_reservado", "pagado", "fallido")
# El sentido lo da el tipo (la cantidad siempre es positiva):
# reserva, venta y ajuste_salida restan; liberacion y ajuste_entrada suman.
# El sentido lo da el tipo (la cantidad siempre es positiva):
# reserva, venta y ajuste_salida restan; liberacion y ajuste_entrada suman.
TIPOS_MOVIMIENTO = ("reserva", "liberacion", "venta", "ajuste_entrada", "ajuste_salida")
ESTADOS_PAGO = ("pendiente", "autorizado", "rechazado")


def _valores_permitidos(columna: str, valores: tuple, nombre: str) -> CheckConstraint:
    lista = ", ".join(f"'{v}'" for v in valores)
    return CheckConstraint(f"{columna} IN ({lista})", name=nombre)


def _creado_en() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (_valores_permitidos("rol", ROLES, "rol"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    correo: Mapped[str] = mapped_column(String(255), unique=True)
    clave_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(20), server_default="cliente")
    creado_en: Mapped[datetime] = _creado_en()


class Producto(Base):
    __tablename__ = "productos"
    __table_args__ = (CheckConstraint("precio >= 0", name="precio"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str | None] = mapped_column(Text)
    precio: Mapped[int]  # pesos chilenos, sin decimales
    activo: Mapped[bool] = mapped_column(server_default=true())


class Inventario(Base):
    __tablename__ = "inventario"
    __table_args__ = (CheckConstraint("cantidad >= 0", name="cantidad"),)

    producto_id: Mapped[int] = mapped_column(
        ForeignKey("productos.id"), primary_key=True, autoincrement=False
    )
    cantidad: Mapped[int]


class Pedido(Base):
    __tablename__ = "pedidos"
    __table_args__ = (_valores_permitidos("estado", ESTADOS_PEDIDO, "estado"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    estado: Mapped[str] = mapped_column(String(20), server_default="pendiente")
    total: Mapped[int]
    creado_en: Mapped[datetime] = _creado_en()

    items: Mapped[list["ItemPedido"]] = relationship(back_populates="pedido")


class ItemPedido(Base):
    __tablename__ = "items_pedido"
    __table_args__ = (CheckConstraint("cantidad > 0", name="cantidad"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad: Mapped[int]
    precio_unitario: Mapped[int]  # precio congelado al momento de comprar

    pedido: Mapped["Pedido"] = relationship(back_populates="items")


class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"
    __table_args__ = (
        _valores_permitidos("tipo", TIPOS_MOVIMIENTO, "tipo"),
        CheckConstraint("cantidad > 0", name="cantidad"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    pedido_id: Mapped[int | None] = mapped_column(ForeignKey("pedidos.id"))
    tipo: Mapped[str] = mapped_column(String(20))
    cantidad: Mapped[int]
    creado_en: Mapped[datetime] = _creado_en()


class Pago(Base):
    __tablename__ = "pagos"
    __table_args__ = (
        _valores_permitidos("estado", ESTADOS_PAGO, "estado"),
        UniqueConstraint("pedido_id", name="uq_pagos_pedido"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"))
    estado: Mapped[str] = mapped_column(String(20), server_default="pendiente")
    monto: Mapped[int]
    referencia_pasarela: Mapped[str | None] = mapped_column(String(100))
    creado_en: Mapped[datetime] = _creado_en()


class ClaveIdempotencia(Base):
    __tablename__ = "claves_idempotencia"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), primary_key=True)
    clave: Mapped[str] = mapped_column(String(100), primary_key=True)
    huella: Mapped[str] = mapped_column(String(64))  # SHA-256 del cuerpo de la solicitud
    codigo_respuesta: Mapped[int | None]
    cuerpo_respuesta: Mapped[dict | None] = mapped_column(JSONB)
    creado_en: Mapped[datetime] = _creado_en()
