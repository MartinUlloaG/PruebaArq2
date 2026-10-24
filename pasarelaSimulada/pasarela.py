# Pasarela de pago simulada (hace como si fuera Webpay o Mercado Pago).
# Corre aparte del servicio de compras, en el puerto 8001.
# Los cobros se guardan en memoria, si se reinicia se borran.
#
# Cada pago trae una clave (Idempotency-Key). Si llega la misma clave otra vez
# se devuelve lo mismo que la primera vez y no se cobra de nuevo.
#
# Modos (se cambian con PUT /simulacion):
#   aprueba -> aprueba todo
#   rechaza -> rechaza todo, como tarjeta sin fondos
#   lenta   -> se demora 5 segundos y después aprueba
#   falla   -> da error 503, como si estuviera caída

import os
import threading
import time
import uuid
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Pasarela simulada")

candado = threading.Lock()  # para que dos pagos al mismo tiempo no se pisen

_estado = {"modo": os.environ.get("PASARELA_MODO", "aprueba")}
_respuestas = {}  # clave -> respuesta que ya se dio
_cobros = []  # pagos aprobados


class Pago(BaseModel):
    pedido_id: int
    monto: int


class Modo(BaseModel):
    modo: Literal["aprueba", "rechaza", "lenta", "falla"]


@app.post("/autorizaciones", summary="Pagar")
def pagar(pago: Pago, clave: str = Header(alias="Idempotency-Key")):
    # si la clave ya llegó antes, se devuelve lo mismo
    with candado:
        if clave in _respuestas:
            return _respuestas[clave]

    modo = _estado["modo"]
    if modo == "falla":
        raise HTTPException(503, "Pasarela caída")
    if modo == "lenta":
        time.sleep(5)

    if modo == "rechaza":
        respuesta = {"autorizado": False, "referencia": None, "motivo": "Fondos insuficientes."}
    else:
        respuesta = {"autorizado": True, "referencia": "AUT-" + uuid.uuid4().hex[:10], "motivo": None}

    with candado:
        # puede que otro pago con la misma clave haya terminado mientras esperaba
        if clave in _respuestas:
            return _respuestas[clave]
        _respuestas[clave] = respuesta
        if respuesta["autorizado"]:
            _cobros.append({"clave": clave, "pedido_id": pago.pedido_id, "monto": pago.monto})
    return respuesta


@app.get("/cobros", summary="Ver cobros")
def ver_cobros():
    return {"total": len(_cobros), "cobros": _cobros}


@app.get("/simulacion", summary="Ver modo")
def ver_modo():
    return _estado


@app.put("/simulacion", summary="Cambiar modo")
def cambiar_modo(nuevo: Modo):
    _estado["modo"] = nuevo.modo
    return _estado


@app.get("/salud", summary="Ver si está prendida")
def salud():
    return {"estado": "ok"}
