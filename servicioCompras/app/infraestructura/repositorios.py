"""Patrón Repository: el único lugar que sabe cómo se consultan las tablas.

Los endpoints piden datos al repositorio; no escriben SQL ni conocen las consultas.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, selectinload

from app.infraestructura.modelos import (
    TIPOS_ENTRADA,
    ClaveIdempotencia,
    EventoProcesado,
    Inventario,
    ItemPedido,
    MovimientoInventario,
    Outbox,
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

    def total_usuarios(self) -> int:
        return self.sesion.scalar(select(func.count()).select_from(Usuario)) or 0


class RepositorioProductos:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def buscar_activo(self, producto_id: int) -> Producto | None:
        return self.sesion.scalar(
            select(Producto).where(Producto.id == producto_id, Producto.activo)
        )

    def total_productos(self) -> int:
        return self.sesion.scalar(select(func.count()).select_from(Producto).where(Producto.activo)) or 0


class RepositorioInventario:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def reservar(self, producto_id: int, cantidad: int, pedido_id: int) -> int | None:
        """Descuenta stock solo si alcanza, y deja el movimiento "reserva" en la auditoría."""
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

    def ajustar_stock(self, producto_id: int, cantidad: int, tipo: str = "ajuste_entrada") -> int:
        """Registra un ajuste o recepción de inventario manteniendo la auditoría (entradas - salidas)."""
        if tipo == "ajuste_salida":
            restante = self.sesion.scalar(
                update(Inventario)
                .where(Inventario.producto_id == producto_id, Inventario.cantidad >= cantidad)
                .values(cantidad=Inventario.cantidad - cantidad)
                .returning(Inventario.cantidad)
            )
            if restante is None:
                raise ValueError("Stock insuficiente para realizar el ajuste de salida.")
        else:
            restante = self.sesion.scalar(
                update(Inventario)
                .where(Inventario.producto_id == producto_id)
                .values(cantidad=Inventario.cantidad + cantidad)
                .returning(Inventario.cantidad)
            )
            if restante is None:
                inv = Inventario(producto_id=producto_id, cantidad=cantidad)
                self.sesion.add(inv)
                self.sesion.flush()
                restante = cantidad
        self.sesion.add(
            MovimientoInventario(producto_id=producto_id, tipo=tipo, cantidad=cantidad)
        )
        return restante

    def total_stock_critico(self, umbral: int = 5) -> int:
        return self.sesion.scalar(
            select(func.count()).select_from(Inventario).where(Inventario.cantidad <= umbral)
        ) or 0

    def saldo_movimientos(self, producto_id: int) -> int:
        """Auditoría: reconstruye el stock solo desde los movimientos (entradas - salidas)."""
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
        self.sesion.flush()
        return pedido

    def buscar_para_actualizar(self, pedido_id: int) -> Pedido | None:
        return self.sesion.scalar(select(Pedido).where(Pedido.id == pedido_id).with_for_update())

    def buscar_de_usuario(self, pedido_id: int, usuario_id: int) -> Pedido | None:
        return self.sesion.scalar(
            select(Pedido).where(Pedido.id == pedido_id, Pedido.usuario_id == usuario_id)
        )

    def reservas_vencidas(self, segundos: int) -> list[Pedido]:
        limite = datetime.now(UTC) - timedelta(seconds=segundos)
        return list(
            self.sesion.scalars(
                select(Pedido)
                .where(Pedido.estado == "stock_reservado", Pedido.creado_en < limite)
                .with_for_update(skip_locked=True)
            )
        )

    def listar_de_usuario(self, usuario_id: int) -> list[Pedido]:
        consulta = (
            select(Pedido)
            .where(Pedido.usuario_id == usuario_id)
            .options(selectinload(Pedido.items).selectinload(ItemPedido.producto))
            .order_by(Pedido.id.desc())
        )
        return list(self.sesion.scalars(consulta))

    def total_pedidos(self) -> int:
        return self.sesion.scalar(select(func.count()).select_from(Pedido)) or 0

    def total_ingresos(self) -> int:
        return self.sesion.scalar(
            select(func.coalesce(func.sum(Pedido.total), 0)).where(
                Pedido.estado.in_(["pagado", "stock_reservado"])
            )
        ) or 0


class RepositorioPagos:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def registrar(self, pedido_id: int, monto: int, estado: str, referencia: str | None) -> Pago:
        pago = Pago(pedido_id=pedido_id, monto=monto, estado=estado, referencia_pasarela=referencia)
        self.sesion.add(pago)
        return pago


class RepositorioIdempotencia:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def tomar(self, usuario_id: int, clave: str, huella: str) -> ClaveIdempotencia | None:
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


class RepositorioOutbox:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def agregar(self, topico: str, clave: str, contenido: dict) -> None:
        self.sesion.add(Outbox(topico=topico, clave=clave, contenido=contenido))


class RepositorioEventos:
    def __init__(self, sesion: Session):
        self.sesion = sesion

    def registrar(self, id_evento: str) -> bool:
        nuevo = self.sesion.scalar(
            insert(EventoProcesado)
            .values(id_evento=id_evento)
            .on_conflict_do_nothing()
            .returning(EventoProcesado.id_evento)
        )
        return nuevo is not None
