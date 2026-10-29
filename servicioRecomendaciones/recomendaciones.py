"""Servicio de recomendaciones: el servicio SECUNDARIO del caso.

Corre en su propio proceso. Sirve para demostrar el aislamiento de fallos: si se
apaga (Ctrl+C), el catálogo y la compra siguen funcionando, y el servicio de compras
solo deja de mostrar la sección de recomendaciones.

Es una simulación: en un sistema real calcularía los destacados desde las ventas.
Aquí devuelve una lista fija de ids de producto (los de la semilla).
"""

from fastapi import FastAPI

app = FastAPI(title="Servicio de recomendaciones")

DESTACADOS = [4, 1, 2, 3]  # monitor, audífonos, teclado, mouse


@app.get("/recomendaciones")
def destacados():
    return {"producto_ids": DESTACADOS}


@app.get("/salud")
def salud():
    return {"estado": "ok"}
