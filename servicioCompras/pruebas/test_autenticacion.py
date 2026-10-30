"""Pieza 2: login con roles y JWT.

Prueba de cierre: un cliente recibe 403 en rutas de operador y de administrador.
Requiere la BD arriba y migrada; la semilla crea los usuarios de demo.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

from app.configuracion import configuracion
from app.infraestructura.base import Sesion
from app.infraestructura.modelos import Usuario
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


# --- Catálogo: cualquier rol con sesión ----------------------------------------


@pytest.mark.parametrize("rol", ["cliente", "operador", "administrador"])
def test_el_catalogo_lo_ve_cualquier_rol_con_sesion(rol):
    respuesta = cliente_http.get("/catalogo", headers=_encabezado(_token(rol)))
    assert respuesta.status_code == 200
    assert {"producto_id", "nombre", "precio", "disponibles"} <= set(respuesta.json()[0])


def test_el_catalogo_sin_sesion_es_401():
    assert cliente_http.get("/catalogo").status_code == 401


# --- Bloqueo por intentos fallidos ---------------------------------------------

CUENTA_BLOQUEO = "cliente98@demo.cl"  # una cuenta aparte, para no bloquear la que usan las otras pruebas


@pytest.fixture
def cuenta_sin_bloqueo():
    def desbloquear():
        with Sesion.begin() as sesion:
            sesion.execute(
                update(Usuario).where(Usuario.correo == CUENTA_BLOQUEO).values(intentos_fallidos=0, bloqueado_hasta=None)
            )

    desbloquear()
    yield
    desbloquear()


def _ingresar(clave: str):
    return cliente_http.post("/autenticacion/ingresar", json={"correo": CUENTA_BLOQUEO, "clave": clave})


def test_3_claves_malas_bloquean_y_no_entregan_jwt_ni_con_la_buena(cuenta_sin_bloqueo):
    _, clave_buena = CLAVES["cliente"]
    codigos = [_ingresar("mala").status_code for _ in range(3)]
    assert codigos == [401, 401, 423]

    con_la_buena = _ingresar(clave_buena)
    assert con_la_buena.status_code == 423
    assert "token_acceso" not in con_la_buena.json()
    assert int(con_la_buena.headers["Retry-After"]) > 0


def test_intentos_simultaneos_se_cuentan_de_a_uno(cuenta_sin_bloqueo):
    """5 intentos malos a la vez: la fila se bloquea (FOR UPDATE), así que se cuentan en
    orden y ninguno se pierde: 2 reciben 401 y desde el tercero, 423."""
    with ThreadPoolExecutor(max_workers=5) as hilos:
        codigos = sorted(hilos.map(lambda _: _ingresar("mala").status_code, range(5)))
    assert codigos == [401, 401, 423, 423, 423]
