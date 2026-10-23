"""Patrón Repository: el único lugar que sabe cómo se consultan las tablas.

Los endpoints piden datos al repositorio; no escriben SQL ni conocen las consultas.
"""

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.infraestructura.modelos import (
    TIPOS_ENTRADA,
    Inventario,
    MovimientoInventario,
    Producto,
    Usuario,
)


class RepositorioUsuarios:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def buscar_por_correo(self, correo: str) -> Usuario | None:
        return self.sesion.scalar(select(Usuario).where(Usuario.correo == correo))

    def listar(self) -> list[Usuario]:
        return list(self.sesion.scalars(select(Usuario).order_by(Usuario.id)))


class RepositorioInventario:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def listar_con_producto(self, solo_activos: bool = False) -> list[tuple[Producto, Inventario]]:
        consulta = (
            select(Producto, Inventario)
            .join(Inventario, Inventario.producto_id == Producto.id)
            .order_by(Producto.id)
        )
        if solo_activos:
            consulta = consulta.where(Producto.activo)
        return [(producto, inventario) for producto, inventario in self.sesion.execute(consulta)]

    def saldo_movimientos(self, producto_id: int) -> int:
        """Auditoría: reconstruye el stock solo desde los movimientos (entradas - salidas).

        Si no coincide con inventario.cantidad, algo cambió el stock sin dejar registro.
        """
        signo = case((MovimientoInventario.tipo.in_(TIPOS_ENTRADA), 1), else_=-1)
        return self.sesion.scalar(
            select(func.coalesce(func.sum(signo * MovimientoInventario.cantidad), 0)).where(
                MovimientoInventario.producto_id == producto_id
            )
        )
