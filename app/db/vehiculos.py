"""Acceso a datos de vehículos. No conoce HTTP: devuelve datos o None/False."""

import uuid
from datetime import datetime, timezone

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError  # noqa: F401  (los routers lo capturan)
from pymongo import ReturnDocument

CAMPOS = ("tipo", "bateriaPct", "estado", "ubicacion", "actualizadoEn")


def ahora() -> datetime:
    # MongoDB guarda milisegundos: se trunca aquí para que lo devuelto coincida con lo guardado.
    t = datetime.now(timezone.utc)
    return t.replace(microsecond=t.microsecond // 1000 * 1000)


def generar_id() -> str:
    return f"veh-{uuid.uuid4().hex[:8]}"


def a_salida(doc: dict) -> dict:
    salida = {"id": doc["_id"], **{c: doc[c] for c in CAMPOS}}
    if "distanciaMetros" in doc:
        salida["distanciaMetros"] = round(doc["distanciaMetros"], 1)
    return salida


async def obtener(coleccion: AsyncCollection, vehiculo_id: str) -> dict | None:
    return await coleccion.find_one({"_id": vehiculo_id})
