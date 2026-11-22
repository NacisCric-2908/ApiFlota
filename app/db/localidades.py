"""Localidades de Bogotá D.C. (20) como referencia geoespacial.

Los datos vienen de Datos Abiertos Bogotá (Catastro Distrital / IDECA, CC BY 4.0), preparados por
scripts/preparar_localidades.py. Se cargan en MongoDB con índice 2dsphere para resolver
«¿en qué localidad está este punto?» con $geoIntersects.
"""

import json
import re
import unicodedata
from pathlib import Path

from pymongo import GEOSPHERE
from pymongo.asynchronous.collection import AsyncCollection

NOMBRE_COLECCION = "localidades"
RUTA_GEOJSON = Path(__file__).resolve().parent.parent / "data" / "localidades_bogota.geojson"


def slug(texto: str) -> str:
    """'Usaquén' -> 'usaquen'; 'La Candelaria' -> 'la-candelaria'."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes.lower()).strip("-")


def referencia(doc: dict) -> dict:
    """Lo que se guarda dentro de cada vehículo. El slug sirve para filtrar sin tildes."""
    return {"codigo": doc["codigo"], "nombre": doc["nombre"], "slug": doc["slug"]}


async def sincronizar(coleccion: AsyncCollection) -> int:
    """Carga (o actualiza) las localidades desde el GeoJSON versionado. Es idempotente."""
    datos = json.loads(RUTA_GEOJSON.read_text(encoding="utf-8"))
    for f in datos["features"]:
        p = f["properties"]
        doc = {
            "_id": p["codigo"],
            "codigo": p["codigo"],
            "nombre": p["nombre"],
            "slug": slug(p["nombre"]),
            "areaM2": p["areaM2"],
            "geometria": f["geometry"],
        }
        await coleccion.replace_one({"_id": doc["_id"]}, doc, upsert=True)
    return len(datos["features"])


async def preparar_indices(coleccion: AsyncCollection) -> None:
    await coleccion.create_index([("geometria", GEOSPHERE)], name="geometria_2dsphere")


async def buscar_por_punto(coleccion: AsyncCollection, lng: float, lat: float) -> dict | None:
    """Localidad que contiene el punto, o None si está fuera de Bogotá."""
    return await coleccion.find_one(
        {"geometria": {"$geoIntersects": {"$geometry": {"type": "Point", "coordinates": [lng, lat]}}}},
        projection={"geometria": 0},
    )


async def obtener(coleccion: AsyncCollection, codigo: str, con_geometria: bool = False) -> dict | None:
    return await coleccion.find_one({"_id": codigo}, projection=None if con_geometria else {"geometria": 0})


async def listar(coleccion: AsyncCollection) -> list[dict]:
    return await coleccion.find({}, projection={"geometria": 0}).sort("_id", 1).to_list(length=None)
