"""Dependencias de FastAPI: corren antes de cada endpoint que las declara."""

from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.infraestructura.base import Sesion
from app.infraestructura.seguridad import TokenInvalido, decodificar_token

# auto_error=False: si falta el encabezado respondemos nosotros, con 401 y mensaje en español.
esquema_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class UsuarioActual:
    id: int
    rol: str


def obtener_sesion() -> Iterator[Session]:
    """Una sesión de BD por solicitud; se cierra sola al terminar."""
    with Sesion() as sesion:
        yield sesion


def _no_autenticado(mensaje: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=mensaje,
        headers={"WWW-Authenticate": "Bearer"},
    )


def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
) -> UsuarioActual:
    """401 si no hay token o no es válido. Solo se confía en lo que viene firmado."""
    if credenciales is None:
        raise _no_autenticado("Debes iniciar sesión.")
    try:
        contenido = decodificar_token(credenciales.credentials)
    except TokenInvalido as error:
        raise _no_autenticado(str(error)) from error
    return UsuarioActual(id=int(contenido["sub"]), rol=contenido["rol"])


def requerir_rol(*roles_permitidos: str):
    """Fábrica de dependencias: 403 si el rol del token no está entre los permitidos."""

    def verificar(usuario: UsuarioActual = Depends(usuario_actual)) -> UsuarioActual:
        if usuario.rol not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para esta acción.",
            )
        return usuario

    return verificar
