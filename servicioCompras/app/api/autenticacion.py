from datetime import UTC, datetime, timedelta

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


def _cuenta_bloqueada(hasta: datetime) -> HTTPException:
    minutos = max(1, round((hasta - datetime.now(UTC)).total_seconds() / 60))
    return HTTPException(
        status.HTTP_423_LOCKED,
        detail=f"Tu cuenta está bloqueada por {configuracion.login_intentos_maximos} intentos fallidos. "
        f"Intenta de nuevo en {minutos} minuto{'s' if minutos > 1 else ''}.",
        headers={"Retry-After": str(int((hasta - datetime.now(UTC)).total_seconds()) + 1)},
    )


@enrutador.post("/ingresar", response_model=RespuestaIngreso)
def ingresar(datos: SolicitudIngreso, sesion: Session = Depends(obtener_sesion)):
    """Con 3 claves malas seguidas la cuenta se bloquea unos minutos (423). Mientras dure
    el bloqueo no se entrega JWT ni con la clave correcta. Los tokens que ya se habían
    entregado siguen valiendo hasta su vencimiento: el bloqueo frena a quien adivina la
    clave, no cierra la sesión del dueño."""
    ahora = datetime.now(UTC)
    usuario = RepositorioUsuarios(sesion).buscar_por_correo(datos.correo.strip().lower(), para_actualizar=True)

    if usuario is not None and usuario.bloqueado_hasta and usuario.bloqueado_hasta > ahora:
        hasheador.verify(datos.clave, HASH_FICTICIO)  # mismo tiempo de respuesta
        raise _cuenta_bloqueada(usuario.bloqueado_hasta)

    clave_correcta = hasheador.verify(datos.clave, usuario.clave_hash if usuario else HASH_FICTICIO)
    if usuario is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Correo o clave incorrectos.")
    if not clave_correcta:
        usuario.intentos_fallidos += 1
        if usuario.intentos_fallidos >= configuracion.login_intentos_maximos:
            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta = ahora + timedelta(minutes=configuracion.login_minutos_bloqueo)
            sesion.commit()
            raise _cuenta_bloqueada(usuario.bloqueado_hasta)
        sesion.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Correo o clave incorrectos.")

    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    sesion.commit()
    return RespuestaIngreso(
        token_acceso=crear_token(usuario.id, usuario.rol),
        expira_en_segundos=configuracion.jwt_minutos * 60,
        usuario=UsuarioPublico(id=usuario.id, correo=usuario.correo, rol=usuario.rol),
    )


@enrutador.get("/yo")
def yo(usuario: UsuarioActual = Depends(usuario_actual)) -> dict:
    """Cualquier usuario autenticado: devuelve quién es según su token."""
    return {"id": usuario.id, "rol": usuario.rol}
