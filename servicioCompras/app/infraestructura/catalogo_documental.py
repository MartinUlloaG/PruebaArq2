"""MongoDB: el catálogo como documentos (lado de LECTURA de CQRS).

Postgres sigue siendo la verdad del stock, el precio y los pedidos (lado de escritura).
Aquí vive lo que se le muestra al cliente: cada prenda es un documento con su categoría
y atributos que cambian según el tipo de prenda (tallas, colores, material...). Eso en
una tabla relacional serían columnas vacías o tablas extra; en un documento no.

El stock de estos documentos es una copia: lo actualiza el proyector cada vez que llega
un evento de catalogo.stock por Kafka (ver trabajadores.py). Puede ir unos milisegundos
atrasado, y está bien: la compra no lee de aquí, reserva contra Postgres con el UPDATE
condicional, así que un stock atrasado en pantalla nunca termina en sobreventa.

Documento:
  {_id: producto_id, nombre, descripcion, categoria, precio, atributos: {...},
   disponibles, version_stock, activo}
"""

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection

from app.configuracion import configuracion

_cliente = MongoClient(configuracion.mongo_url, serverSelectionTimeoutMS=3000)
catalogo: Collection = _cliente[configuracion.mongo_db]["catalogo"]


def _a_producto(documento: dict) -> dict:
    return {
        "producto_id": documento["_id"],
        "nombre": documento["nombre"],
        "descripcion": documento.get("descripcion"),
        "categoria": documento["categoria"],
        "precio": documento["precio"],
        "atributos": documento.get("atributos", {}),
        "disponibles": documento.get("disponibles", 0),
    }


class RepositorioCatalogo:
    def __init__(self, coleccion: Collection = catalogo):
        self.coleccion = coleccion

    def crear_indices(self) -> None:
        self.coleccion.create_index([("categoria", ASCENDING), ("nombre", ASCENDING)])

    def listar(self, categoria: str | None = None) -> list[dict]:
        filtro = {"activo": True}
        if categoria:
            filtro["categoria"] = categoria
        return [_a_producto(d) for d in self.coleccion.find(filtro).sort([("categoria", 1), ("nombre", 1)])]

    def categorias(self) -> list[dict]:
        """Cuántas prendas hay por categoría, calculado en Mongo (no escrito a mano en el front)."""
        grupos = self.coleccion.aggregate(
            [
                {"$match": {"activo": True}},
                {"$group": {"_id": "$categoria", "productos": {"$sum": 1}, "unidades": {"$sum": "$disponibles"}}},
                {"$sort": {"_id": 1}},
            ]
        )
        return [{"nombre": g["_id"], "productos": g["productos"], "unidades": g["unidades"]} for g in grupos]

    def por_id(self, ids: list[int]) -> dict[int, dict]:
        return {d["_id"]: _a_producto(d) for d in self.coleccion.find({"_id": {"$in": list(ids)}})}

    def guardar(self, producto_id: int, datos: dict) -> None:
        """Alta o reemplazo completo de una prenda (lo usa la semilla)."""
        self.coleccion.replace_one({"_id": producto_id}, {"_id": producto_id, **datos}, upsert=True)

    def actualizar_stock(self, producto_id: int, disponibles: int, version: int) -> bool:
        """Proyección del stock. Solo escribe si la versión es más nueva que la guardada.

        La versión es el id del movimiento de inventario, que crece en el mismo orden en
        que Postgres bloqueó la fila. Así un evento repetido o que llega tarde no pisa un
        stock más nuevo: el proyector es idempotente sin tabla de eventos procesados.
        """
        resultado = self.coleccion.update_one(
            {"_id": producto_id, "version_stock": {"$lt": version}},
            {"$set": {"disponibles": disponibles, "version_stock": version}},
        )
        return resultado.modified_count == 1

    def borrar_todo(self) -> None:
        self.coleccion.delete_many({})
