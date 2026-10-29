"""Semilla oficial de base de datos KYRO: catálogo limpio de 20 prendas y usuarios por rol.

Elimina definitivamente de la base de datos cualquier producto tecnológico heredado
(audífonos, teclados, mouse, monitores, webcams, consolas) e inserta el catálogo textil
oficial de marca KYRO ordenado por líneas de producto.

Uso, desde servicioCompras:  python -m app.infraestructura.semilla
"""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.infraestructura.base import Sesion
from app.infraestructura.modelos import (
    Inventario,
    ItemPedido,
    MovimientoInventario,
    Producto,
    Usuario,
)
from app.infraestructura.seguridad import hasheador

USUARIOS_DEMO = [
    # (correo, clave de demo, rol)
    ("cliente@demo.cl", "Cliente-Demo-2026", "cliente"),
    ("operador@demo.cl", "Operador-Demo-2026", "operador"),
    ("admin@demo.cl", "Admin-Demo-2026", "administrador"),
]

# Catálogo oficial KYRO: 20 productos de ropa ordenados por categorías exactas
# (nombre, descripción, precio en CLP, stock inicial)
PRODUCTOS_DEMO = [
    # --- 1. POLERONES (4 piezas) ---
    (
        "Polerón Oversize Navy",
        "Polerón de calce holgado en fleece pesado 450g tono azul marino",
        44990,
        25,
    ),
    (
        "Polerón con Cierre Ice",
        "Polerón con cierre frontal metálico oculto en tono hielo glacial",
        48990,
        20,
    ),
    (
        "Polerón Minimal Black",
        "Crewneck cuello redondo en algodón perchado negro monocromático",
        39990,
        30,
    ),
    (
        "Polerón Crewneck Heather",
        "Cuello redondo en gris jaspeado clásico con acabados al corte",
        42990,
        1,  # Stock 1: reservado para prueba de sobreventa bajo concurrencia
    ),

    # --- 2. POLERAS (4 piezas) ---
    (
        "Polera Básica Fit",
        "Algodón peinado premium 240g de calce estándar contemporáneo",
        18990,
        45,
    ),
    (
        "Polera Estampada Editorial",
        "Serigrafía tipográfica sutil al agua con caída relajada",
        22990,
        35,
    ),
    (
        "Polera Manga Larga Raw",
        "Manga larga en algodón mercerizado con puños sin costura",
        24990,
        30,
    ),
    (
        "Polera Boxy Heavyweight",
        "Silueta cuadrada en algodón de 300g con hombros estructurados",
        26990,
        15,
    ),

    # --- 3. CALCETINES (4 piezas) ---
    (
        "Pack Calcetines Altos Sport",
        "Pack de 3 pares acanalados a media pantorrilla con planta acolchada",
        12990,
        50,
    ),
    (
        "Calcetines Térmicos Waffle",
        "Tejido panal térmico transpirable en mezcla de lana merino",
        14990,
        40,
    ),
    (
        "Calcetín Ribbed High-Gauge",
        "Punto ultra compacto de alta elasticidad para calzado formal o urbano",
        11990,
        35,
    ),
    (
        "Calcetines Tobilleros Minimal",
        "Pack de 3 pares corte bajo invisible con sujeción anatómica",
        9990,
        4,  # Stock crítico para validar alertas de reposición
    ),

    # --- 4. GORRAS (4 piezas) ---
    (
        "Gorra Dad Hat Kyro",
        "Gorra desestructurada en gabardina de algodón lavado con broche metálico",
        18990,
        25,
    ),
    (
        "Gorra Snapback Minimal",
        "Corona de seis paneles estructurada con visera plana contemporánea",
        21990,
        20,
    ),
    (
        "Gorra Cotton Twill Beige",
        "Sarga de algodón peinado en tono arena con bordado tonal sutil",
        19990,
        22,
    ),
    (
        "Beanie Merino Extra Fino",
        "Gorro tejido en lana merino extrafina de tacto ultrasuave",
        22990,
        18,
    ),

    # --- 5. BLUSAS / PANTALONES (4 piezas) ---
    (
        "Blusa Lino Estructurada",
        "Blusa escandinava de corte recto en lino lavado artesanal",
        36990,
        0,  # Agotado para probar UX de producto sin stock
    ),
    (
        "Pantalón Cargo Editorial",
        "Pantalón de corte recto con bolsillos discretos de fuelle en sarga pesada",
        46990,
        20,
    ),
    (
        "Camisa Popelina Oversize",
        "Camisa clásica con cuello italiano y botonadura de nácar oculta",
        38990,
        25,
    ),
    (
        "Pantalón Wide Leg Chino",
        "Pantalón de tiro medio y pernera ancha en algodón twill estructurado",
        44990,
        15,
    ),
]

# Términos que identifican artículos tecnológicos a eliminar
TERMINOS_TECNOLOGICOS = (
    "audífono",
    "audifono",
    "teclado",
    "mouse",
    "monitor",
    "webcam",
    "consola",
    "inalámbrico",
    "inalambrico",
    "bluetooth",
    "auricular",
    "switches",
    "ergonómico",
    "ergonomico",
)


def _eliminar_productos_tecnologicos(sesion: Session) -> int:
    """Elimina definitivamente de la base de datos cualquier producto no textil.

    Limpia en cascada items_pedido, movimientos_inventario, inventario y productos
    respetando las restricciones de integridad referencial.
    """
    productos = sesion.scalars(select(Producto)).all()
    ids_a_borrar = [
        p.id
        for p in productos
        if any(
            t in p.nombre.lower() or (p.descripcion and t in p.descripcion.lower())
            for t in TERMINOS_TECNOLOGICOS
        )
    ]
    if not ids_a_borrar:
        return 0

    # 1. Eliminar ítems de pedido asociados a productos tecnológicos
    sesion.execute(delete(ItemPedido).where(ItemPedido.producto_id.in_(ids_a_borrar)))
    # 2. Eliminar movimientos de inventario asociados
    sesion.execute(delete(MovimientoInventario).where(MovimientoInventario.producto_id.in_(ids_a_borrar)))
    # 3. Eliminar inventario
    sesion.execute(delete(Inventario).where(Inventario.producto_id.in_(ids_a_borrar)))
    # 4. Eliminar productos
    sesion.execute(delete(Producto).where(Producto.id.in_(ids_a_borrar)))

    return len(ids_a_borrar)


def _crear_usuarios(sesion: Session) -> int:
    creados = 0
    for correo, clave, rol in USUARIOS_DEMO:
        existe = sesion.scalar(select(Usuario.id).where(Usuario.correo == correo))
        if existe is None:
            sesion.add(Usuario(correo=correo, clave_hash=hasheador.hash(clave), rol=rol))
            creados += 1
    return creados


def _crear_o_actualizar_prendas(sesion: Session) -> tuple[int, int]:
    creados = 0
    actualizados = 0
    for nombre, descripcion, precio, stock in PRODUCTOS_DEMO:
        producto = sesion.scalar(select(Producto).where(Producto.nombre == nombre))
        if producto is not None:
            # Mantener sincronizado precio, descripción y estado activo
            producto.descripcion = descripcion
            producto.precio = precio
            producto.activo = True
            actualizados += 1
            continue

        # Inserción de nueva prenda oficial KYRO
        producto = Producto(nombre=nombre, descripcion=descripcion, precio=precio, activo=True)
        sesion.add(producto)
        sesion.flush()  # Obtener producto.id

        sesion.add(Inventario(producto_id=producto.id, cantidad=stock))
        if stock > 0:
            sesion.add(
                MovimientoInventario(producto_id=producto.id, tipo="ajuste_entrada", cantidad=stock)
            )
        creados += 1

    return creados, actualizados


def sembrar() -> tuple[int, int, int, int]:
    """Ejecuta la purga de productos tecnológicos y la inserción del catálogo oficial de ropa en una sola transacción ACID."""
    with Sesion.begin() as sesion:
        purgados = _eliminar_productos_tecnologicos(sesion)
        usuarios = _crear_usuarios(sesion)
        creados, actualizados = _crear_o_actualizar_prendas(sesion)
        return purgados, usuarios, creados, actualizados


if __name__ == "__main__":
    purgados, usuarios, creados, actualizados = sembrar()
    print(
        f"Semilla KYRO ejecutada con éxito:\n"
        f"  - Productos tecnológicos eliminados de la BD: {purgados}\n"
        f"  - Usuarios demo verificados/creados: {usuarios}\n"
        f"  - Prendas oficiales insertadas: {creados}\n"
        f"  - Prendas sincronizadas existentes: {actualizados}"
    )
