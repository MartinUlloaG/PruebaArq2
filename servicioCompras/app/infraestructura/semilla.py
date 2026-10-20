"""Datos de demostración: un usuario por rol y un catálogo chico con stock.

Se puede correr varias veces sin duplicar nada (busca antes de insertar).
Uso, desde servicioCompras:  python -m app.infraestructura.semilla

LAS CLAVES DE ESTOS USUARIOS SON SOLO DE DEMO. En la BD se guardan con hash
Argon2; nunca reutilizarlas fuera de este proyecto.
"""

from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infraestructura.base import Sesion
from app.infraestructura.modelos import Inventario, MovimientoInventario, Producto, Usuario

# Argon2id con los parámetros recomendados por pwdlib.
hasheador = PasswordHash.recommended()

USUARIOS_DEMO = [
    # (correo, clave de demo, rol)
    ("cliente@demo.cl", "Cliente-Demo-2026", "cliente"),
    ("operador@demo.cl", "Operador-Demo-2026", "operador"),
    ("admin@demo.cl", "Admin-Demo-2026", "administrador"),
]

PRODUCTOS_DEMO = [
    # (nombre, descripción, precio en CLP, stock inicial)
    ("Audífonos inalámbricos", "Bluetooth 5.3, 30 horas de batería", 39990, 25),
    ("Teclado mecánico", "Switches rojos, distribución latinoamericana", 54990, 15),
    ("Mouse ergonómico", "Vertical, 6 botones", 24990, 40),
    ("Monitor 27 pulgadas", "IPS, 1440p, 165 Hz", 249990, 8),
    ("Webcam Full HD", "1080p, micrófono incorporado", 32990, 0),  # agotado: para probar la UI
    ("Consola edición limitada", "Una sola unidad: prueba de sobreventa", 499990, 1),
]


def _crear_usuarios(sesion: Session) -> int:
    creados = 0
    for correo, clave, rol in USUARIOS_DEMO:
        existe = sesion.scalar(select(Usuario.id).where(Usuario.correo == correo))
        if existe is None:
            sesion.add(Usuario(correo=correo, clave_hash=hasheador.hash(clave), rol=rol))
            creados += 1
    return creados


def _crear_productos(sesion: Session) -> int:
    creados = 0
    for nombre, descripcion, precio, stock in PRODUCTOS_DEMO:
        existe = sesion.scalar(select(Producto.id).where(Producto.nombre == nombre))
        if existe is not None:
            continue  # no se pisa el stock de un producto que ya existe
        producto = Producto(nombre=nombre, descripcion=descripcion, precio=precio)
        sesion.add(producto)
        sesion.flush()  # obtiene producto.id sin cerrar la transacción
        sesion.add(Inventario(producto_id=producto.id, cantidad=stock))
        if stock > 0:
            # El stock inicial también queda en la auditoría: suma de movimientos = stock.
            sesion.add(
                MovimientoInventario(producto_id=producto.id, tipo="ajuste_entrada", cantidad=stock)
            )
        creados += 1
    return creados


def sembrar() -> tuple[int, int]:
    """Inserta lo que falte, todo en una sola transacción. Devuelve (usuarios, productos) creados."""
    with Sesion.begin() as sesion:
        return _crear_usuarios(sesion), _crear_productos(sesion)


if __name__ == "__main__":
    usuarios, productos = sembrar()
    print(f"Usuarios creados: {usuarios}. Productos creados: {productos}.")
