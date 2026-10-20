"""Patrón Repository: el único lugar que sabe cómo se consultan las tablas.

Los endpoints piden datos al repositorio; no escriben SQL ni conocen las consultas.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infraestructura.modelos import Inventario, Producto, Usuario


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

    def listar_con_producto(self) -> list[tuple[Producto, Inventario]]:
        consulta = (
            select(Producto, Inventario)
            .join(Inventario, Inventario.producto_id == Producto.id)
            .order_by(Producto.id)
        )
        return [(producto, inventario) for producto, inventario in self.sesion.execute(consulta)]
