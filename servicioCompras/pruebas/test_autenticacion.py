"""Pieza 2: login con roles y JWT.

Prueba de cierre: un cliente recibe 403 en rutas de operador y de administrador.
Requiere la BD arriba y migrada; la semilla crea los usuarios de demo.
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from app.configuracion import configuracion
from app.infraestructura.semilla import USUARIOS_DEMO, sembrar
from app.principal import app

cliente_http = TestClient(app)
CLAVES = {rol: (correo, clave) for correo, clave, rol in USUARIOS_DEMO}


@pytest.fixture(scope="module", autouse=True)
def datos_demo():
    sembrar()


def _token(rol: str) -> str:
    correo, clave = CLAVES[rol]
    respuesta = cliente_http.post("/autenticacion/ingresar", json={"correo": correo, "clave": clave})
    assert respuesta.status_code == 200
    return respuesta.json()["token_acceso"]


def _encabezado(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --- Ingreso ---------------------------------------------------------------


def test_ingreso_correcto_devuelve_token_y_rol():
    correo, clave = CLAVES["cliente"]
    respuesta = cliente_http.post("/autenticacion/ingresar", json={"correo": correo, "clave": clave})
    cuerpo = respuesta.json()
    assert respuesta.status_code == 200
    assert cuerpo["usuario"]["rol"] == "cliente"
    assert "clave_hash" not in cuerpo["usuario"]


def test_correo_con_mayusculas_y_espacios_tambien_ingresa():
    correo, clave = CLAVES["cliente"]
    respuesta = cliente_http.post(
        "/autenticacion/ingresar", json={"correo": f"  {correo.upper()} ", "clave": clave}
    )
    assert respuesta.status_code == 200


def test_clave_incorrecta_y_correo_inexistente_dan_el_mismo_mensaje():
    correo, _ = CLAVES["cliente"]
    mala_clave = cliente_http.post(
        "/autenticacion/ingresar", json={"correo": correo, "clave": "incorrecta"}
    )
    sin_correo = cliente_http.post(
        "/autenticacion/ingresar", json={"correo": "nadie@demo.cl", "clave": "incorrecta"}
    )
    assert mala_clave.status_code == sin_correo.status_code == 401
    assert mala_clave.json() == sin_correo.json()  # no delata qué correos existen


# --- 401: no sé quién eres ------------------------------------------------------


def test_sin_token_es_401():
    assert cliente_http.get("/autenticacion/yo").status_code == 401


def test_token_con_rol_adulterado_es_401():
    """Cambiar el rol dentro del token rompe la firma."""
    cabecera, contenido, firma = _token("cliente").split(".")
    falso = jwt.encode({"sub": "1", "rol": "administrador", "exp": 9999999999}, "un-secreto-distinto-al-del-servidor-de-32-bytes")
    _, contenido_falso, _ = falso.split(".")
    adulterado = f"{cabecera}.{contenido_falso}.{firma}"
    respuesta = cliente_http.get("/administracion/usuarios", headers=_encabezado(adulterado))
    assert respuesta.status_code == 401


def test_token_vencido_es_401():
    vencido = jwt.encode(
        {"sub": "1", "rol": "cliente", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        configuracion.jwt_secreto,
        algorithm="HS256",
    )
    respuesta = cliente_http.get("/autenticacion/yo", headers=_encabezado(vencido))
    assert respuesta.status_code == 401
    assert "expiró" in respuesta.json()["detail"]


# --- 403: sé quién eres, pero no puedes (prueba de cierre) ----------------------


@pytest.mark.parametrize(
    ("rol", "ruta", "codigo_esperado"),
    [
        ("cliente", "/inventario", 403),
        ("cliente", "/administracion/usuarios", 403),
        ("operador", "/inventario", 200),
        ("operador", "/administracion/usuarios", 403),
        ("administrador", "/inventario", 200),
        ("administrador", "/administracion/usuarios", 200),
    ],
)
def test_permisos_por_rol(rol, ruta, codigo_esperado):
    respuesta = cliente_http.get(ruta, headers=_encabezado(_token(rol)))
    assert respuesta.status_code == codigo_esperado


def test_la_lista_de_usuarios_no_expone_hashes():
    respuesta = cliente_http.get("/administracion/usuarios", headers=_encabezado(_token("administrador")))
    assert all(set(u) == {"id", "correo", "rol"} for u in respuesta.json())
