"""Rutas solo para administradores (panel de usuarios y métricas ejecutivas)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.autenticacion import UsuarioPublico
from app.api.dependencias import obtener_sesion, requerir_rol
from app.infraestructura.repositorios import (
    RepositorioInventario,
    RepositorioPedidos,
    RepositorioProductos,
    RepositorioUsuarios,
)

enrutador = APIRouter(
    prefix="/administracion",
    tags=["administración"],
    dependencies=[Depends(requerir_rol("administrador"))],  # aplica a todas las rutas del grupo
)


class ResumenEjecutivo(BaseModel):
    total_usuarios: int
    total_pedidos: int
    ingresos_totales: int
    stock_critico: int
    total_productos: int


@enrutador.get("/usuarios", response_model=list[UsuarioPublico])
def listar_usuarios(sesion: Session = Depends(obtener_sesion)):
    # response_model filtra los campos: clave_hash nunca sale en la respuesta.
    return RepositorioUsuarios(sesion).listar()


@enrutador.get("/resumen", response_model=ResumenEjecutivo)
def obtener_resumen_ejecutivo(sesion: Session = Depends(obtener_sesion)):
    usuarios_repo = RepositorioUsuarios(sesion)
    pedidos_repo = RepositorioPedidos(sesion)
    inventario_repo = RepositorioInventario(sesion)
    productos_repo = RepositorioProductos(sesion)

    return ResumenEjecutivo(
        total_usuarios=usuarios_repo.total_usuarios(),
        total_pedidos=pedidos_repo.total_pedidos(),
        ingresos_totales=pedidos_repo.total_ingresos(),
        stock_critico=inventario_repo.total_stock_critico(umbral=5),
        total_productos=productos_repo.total_productos(),
    )
