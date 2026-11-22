from fastapi import Request
from pymongo import ASCENDING, GEOSPHERE, AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection

NOMBRE_COLECCION = "vehiculos"


def crear_cliente(uri: str) -> AsyncMongoClient:
    # tz_aware: las fechas se leen como UTC con zona horaria, no "ingenuas".
    return AsyncMongoClient(uri, tz_aware=True, serverSelectionTimeoutMS=5000)


async def preparar_indices(coleccion: AsyncCollection) -> None:
    # Índice geoespacial exigido por el enunciado para las búsquedas por cercanía.
    await coleccion.create_index([("ubicacion", GEOSPHERE)], name="ubicacion_2dsphere")
    await coleccion.create_index([("estado", ASCENDING)], name="estado_1")
    await coleccion.create_index([("localidad.slug", ASCENDING)], name="localidad_slug_1")


def obtener_coleccion(request: Request) -> AsyncCollection:
    return request.app.state.vehiculos


def obtener_localidades(request: Request) -> AsyncCollection:
    return request.app.state.localidades
