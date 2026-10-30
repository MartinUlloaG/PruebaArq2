"""Hash de claves (Argon2id) y tokens JWT firmados con HS256."""

from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.configuracion import configuracion

ALGORITMO = "HS256"

hasheador = PasswordHash.recommended()


HASH_FICTICIO = hasheador.hash("clave-ficticia-para-igualar-tiempos")


class TokenInvalido(Exception):
    """El token no se pudo validar (firma alterada, vencido o mal formado)."""


def crear_token(usuario_id: int, rol: str) -> str:
    ahora = datetime.now(timezone.utc)
    contenido = {
        "sub": str(usuario_id),  # el estándar exige que "sub" sea texto
        "rol": rol,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=configuracion.jwt_minutos),
    }
    return jwt.encode(contenido, configuracion.jwt_secreto, algorithm=ALGORITMO)


def decodificar_token(token: str) -> dict:
    """Verifica firma y expiración. Lanza TokenInvalido si algo no cuadra."""
    try:
        return jwt.decode(
            token,
            configuracion.jwt_secreto,
            algorithms=[ALGORITMO],  # lista fija: impide que el token elija otro algoritmo
            options={"require": ["sub", "rol", "exp"]},
        )
    except jwt.ExpiredSignatureError as error:
        raise TokenInvalido("Tu sesión expiró. Vuelve a ingresar.") from error
    except jwt.InvalidTokenError as error:
        raise TokenInvalido("Sesión inválida. Vuelve a ingresar.") from error
