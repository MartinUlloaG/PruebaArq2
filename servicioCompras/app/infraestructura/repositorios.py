"""Patrón Repository: el único lugar que sabe cómo se consultan las tablas.

Los endpoints piden datos al repositorio; no escriben SQL ni conocen las consultas.
"""

from sqlalchemy import case, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, selectinload

from app.infraestructura.modelos import (
    TIPOS_ENTRADA,
    ClaveIdempotencia,
    Inventario,
    ItemPedido,
    MovimientoInventario,
    Pago,
    Pedido,
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


class RepositorioProductos:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def buscar_activo(self, producto_id: int) -> Producto | None:
        return self.sesion.scalar(
            select(Producto).where(Producto.id == producto_id, Producto.activo)
        )


class RepositorioInventario:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def reservar(self, producto_id: int, cantidad: int, pedido_id: int) -> int | None:
        """Descuenta stock solo si alcanza, y deja el movimiento "reserva" en la auditoría.

        UPDATE condicional: la condición (cantidad >= n) se evalúa en la misma instrucción
        que escribe. Si dos compras llegan juntas, Postgres bloquea la fila; la segunda
        espera y vuelve a evaluar la condición con el stock ya descontado.
        Devuelve el stock que queda, o None si no alcanzaba (no se tocó nada).
        """
        restante = self.sesion.scalar(
            update(Inventario)
            .where(Inventario.producto_id == producto_id, Inventario.cantidad >= cantidad)
            .values(cantidad=Inventario.cantidad - cantidad)
            .returning(Inventario.cantidad)
        )
        if restante is not None:
            self.sesion.add(
                MovimientoInventario(
                    producto_id=producto_id, pedido_id=pedido_id, tipo="reserva", cantidad=cantidad
                )
            )
        return restante

    def liberar(self, producto_id: int, cantidad: int, pedido_id: int) -> None:
        """Compensación de la Saga: devuelve al stock lo que se reservó, con su movimiento."""
        self.sesion.execute(
            update(Inventario)
            .where(Inventario.producto_id == producto_id)
            .values(cantidad=Inventario.cantidad + cantidad)
        )
        self.sesion.add(
            MovimientoInventario(
                producto_id=producto_id, pedido_id=pedido_id, tipo="liberacion", cantidad=cantidad
            )
        )

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


class RepositorioPedidos:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def crear(self, usuario_id: int, producto: Producto, cantidad: int, estado: str) -> Pedido:
        """El precio se copia al ítem: si el producto cambia de precio, el pedido no cambia."""
        pedido = Pedido(
            usuario_id=usuario_id,
            estado=estado,
            total=producto.precio * cantidad,
            items=[
                ItemPedido(
                    producto_id=producto.id, cantidad=cantidad, precio_unitario=producto.precio
                )
            ],
        )
        self.sesion.add(pedido)
        self.sesion.flush()  # obtiene pedido.id sin cerrar la transacción
        return pedido

    def listar_de_usuario(self, usuario_id: int) -> list[Pedido]:
        consulta = (
            select(Pedido)
            .where(Pedido.usuario_id == usuario_id)
            .options(selectinload(Pedido.items).selectinload(ItemPedido.producto))
            .order_by(Pedido.id.desc())
        )
        return list(self.sesion.scalars(consulta))


class RepositorioPagos:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def registrar(self, pedido_id: int, monto: int, estado: str, referencia: str | None) -> Pago:
        """Guarda la respuesta de la pasarela. UNIQUE(pedido_id): un solo pago por pedido."""
        pago = Pago(pedido_id=pedido_id, monto=monto, estado=estado, referencia_pasarela=referencia)
        self.sesion.add(pago)
        return pago


class RepositorioIdempotencia:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def tomar(self, usuario_id: int, clave: str, huella: str) -> ClaveIdempotencia | None:
        """Intenta registrar la clave. Devuelve None si es nueva, o la fila que ya existía.

        INSERT ... ON CONFLICT DO NOTHING es atómico: si dos solicitudes con la misma
        clave llegan juntas, solo una la inserta. No es "consultar y luego insertar",
        que tendría la misma condición de carrera que la sobreventa.
        """
        insertada = self.sesion.scalar(
            insert(ClaveIdempotencia)
            .values(usuario_id=usuario_id, clave=clave, huella=huella)
            .on_conflict_do_nothing()
            .returning(ClaveIdempotencia.clave)
        )
        if insertada is not None:
            return None
        return self.sesion.get(ClaveIdempotencia, (usuario_id, clave))

    def guardar_respuesta(self, usuario_id: int, clave: str, codigo: int, cuerpo: dict) -> None:
        self.sesion.execute(
            update(ClaveIdempotencia)
            .where(ClaveIdempotencia.usuario_id == usuario_id, ClaveIdempotencia.clave == clave)
            .values(codigo_respuesta=codigo, cuerpo_respuesta=cuerpo)
        )
