from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencias import UsuarioActual, obtener_sesion, usuario_actual
from app.configuracion import configuracion
from app.infraestructura.repositorios import RepositorioUsuarios
from app.infraestructura.seguridad import HASH_FICTICIO, crear_token, hasheador

enrutador = APIRouter(prefix="/autenticacion", tags=["autenticación"])


class SolicitudIngreso(BaseModel):
    correo: str = Field(min_length=3, max_length=255)
    clave: str = Field(min_length=1, max_length=128)


class UsuarioPublico(BaseModel):
    """Lo único que sale de un usuario hacia afuera (nunca clave_hash)."""

    id: int
    correo: str
    rol: str


class RespuestaIngreso(BaseModel):
    token_acceso: str
    tipo_token: str = "bearer"
    expira_en_segundos: int
    usuario: UsuarioPublico


@enrutador.post("/ingresar", response_model=RespuestaIngreso)
def ingresar(datos: SolicitudIngreso, sesion: Session = Depends(obtener_sesion)):
    usuario = RepositorioUsuarios(sesion).buscar_por_correo(datos.correo.strip().lower())

    # Siempre se verifica un hash (el real o uno ficticio): mismo tiempo de respuesta
    # y mismo mensaje, exista o no el correo.
    clave_correcta = hasheador.verify(datos.clave, usuario.clave_hash if usuario else HASH_FICTICIO)
    if usuario is None or not clave_correcta:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Correo o clave incorrectos.")

    return RespuestaIngreso(
        token_acceso=crear_token(usuario.id, usuario.rol),
        expira_en_segundos=configuracion.jwt_minutos * 60,
        usuario=UsuarioPublico(id=usuario.id, correo=usuario.correo, rol=usuario.rol),
    )


@enrutador.get("/yo")
def yo(usuario: UsuarioActual = Depends(usuario_actual)) -> dict:
    """Cualquier usuario autenticado: devuelve quién es según su token."""
    return {"id": usuario.id, "rol": usuario.rol}
