"""Rutas solo para administradores (panel de usuarios)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.autenticacion import UsuarioPublico
from app.api.dependencias import obtener_sesion, requerir_rol
from app.infraestructura.repositorios import RepositorioUsuarios

enrutador = APIRouter(
    prefix="/administracion",
    tags=["administración"],
    dependencies=[Depends(requerir_rol("administrador"))],  # aplica a todas las rutas del grupo
)


@enrutador.get("/usuarios", response_model=list[UsuarioPublico])
def listar_usuarios(sesion: Session = Depends(obtener_sesion)):
    # response_model filtra los campos: clave_hash nunca sale en la respuesta.
    return RepositorioUsuarios(sesion).listar()
