"""Acceso a datos de vehículos. No conoce HTTP: devuelve datos o None/False."""

import uuid
from datetime import datetime, timezone

from pymongo import ReturnDocument
from pymongo.asynchronous.collection import AsyncCollection

CAMPOS = ("tipo", "bateriaPct", "estado", "ubicacion", "actualizadoEn")


def ahora() -> datetime:
    # MongoDB guarda milisegundos: se trunca aquí para que lo devuelto coincida con lo guardado.
    t = datetime.now(timezone.utc)
    return t.replace(microsecond=t.microsecond // 1000 * 1000)


def generar_id() -> str:
    return f"veh-{uuid.uuid4().hex[:8]}"


def a_salida(doc: dict) -> dict:
    salida = {"id": doc["_id"], **{c: doc[c] for c in CAMPOS}}
    if doc.get("localidad"):  # sin el slug, que es de uso interno
        salida["localidad"] = {k: doc["localidad"][k] for k in ("codigo", "nombre")}
    if "distanciaMetros" in doc:
        salida["distanciaMetros"] = round(doc["distanciaMetros"], 1)
    return salida


async def obtener(coleccion: AsyncCollection, vehiculo_id: str) -> dict | None:
    return await coleccion.find_one({"_id": vehiculo_id})


async def crear(coleccion: AsyncCollection, datos: dict) -> dict:
    """Inserta un vehículo. Lanza DuplicateKeyError si el id ya existe."""
    doc = {"_id": datos.get("id") or generar_id(), **{k: v for k, v in datos.items() if k != "id"}}
    doc["actualizadoEn"] = ahora()
    await coleccion.insert_one(doc)
    return doc


async def reemplazar(coleccion: AsyncCollection, vehiculo_id: str, datos: dict) -> dict | None:
    doc = {**datos, "actualizadoEn": ahora()}
    return await coleccion.find_one_and_replace(
        {"_id": vehiculo_id}, doc, return_document=ReturnDocument.AFTER
    )


async def listar(
    coleccion: AsyncCollection,
    filtro: dict,
    pagina: int,
    tamano: int,
    cerca_de: tuple[float, float, float] | None = None,
) -> tuple[list[dict], int]:
    """Lista paginada. Con `cerca_de=(lat, lng, radio_m)` ordena por distancia ascendente."""
    saltar = (pagina - 1) * tamano

    if cerca_de is None:
        total = await coleccion.count_documents(filtro)
        cursor = coleccion.find(filtro).sort("_id", 1).skip(saltar).limit(tamano)
        return await cursor.to_list(length=tamano), total

    lat, lng, radio = cerca_de
    pipeline = [
        {
            "$geoNear": {
                "near": {"type": "Point", "coordinates": [lng, lat]},
                "distanceField": "distanciaMetros",
                "maxDistance": radio,
                "spherical": True,
                "query": filtro,
            }
        },
        {
            "$facet": {
                "items": [{"$skip": saltar}, {"$limit": tamano}],
                "total": [{"$count": "n"}],
            }
        },
    ]
    cursor = await coleccion.aggregate(pipeline)
    resultado = (await cursor.to_list(length=1))[0]
    total = resultado["total"][0]["n"] if resultado["total"] else 0
    return resultado["items"], total


async def eliminar(coleccion: AsyncCollection, vehiculo_id: str) -> str:
    """Borra de forma atómica salvo que esté en viaje. Devuelve 'eliminado', 'no_existe' o 'en_viaje'."""
    resultado = await coleccion.delete_one({"_id": vehiculo_id, "estado": {"$ne": "en_viaje"}})
    if resultado.deleted_count:
        return "eliminado"
    existe = await coleccion.count_documents({"_id": vehiculo_id}, limit=1)
    return "en_viaje" if existe else "no_existe"


# Transiciones válidas, indexadas por el estado destino.
# Un cambio al mismo estado (p. ej. en_viaje -> en_viaje) nunca es válido.
ORIGENES_PERMITIDOS = {
    "en_viaje": ["disponible"],
    "disponible": ["en_viaje", "mantenimiento"],
    "mantenimiento": ["disponible", "en_viaje"],
}


async def cambiar_estado(
    coleccion: AsyncCollection, vehiculo_id: str, cambio: dict
) -> tuple[dict | None, dict | None]:
    """Cambia el estado de forma atómica (una sola operación con condición sobre el estado actual).

    Si dos peticiones compiten por el mismo vehículo, MongoDB serializa las escrituras sobre el
    documento: la segunda ya no cumple el filtro y no modifica nada.

    Devuelve (documento_actualizado, None) si ganó, o (None, documento_actual) si no se pudo.
    El documento actual es None cuando el vehículo no existe.
    """
    nuevo = {"estado": cambio["estado"], "actualizadoEn": ahora()}
    for campo in ("ubicacion", "bateriaPct", "localidad"):
        if cambio.get(campo) is not None:
            nuevo[campo] = cambio[campo]

    actualizado = await coleccion.find_one_and_update(
        {"_id": vehiculo_id, "estado": {"$in": ORIGENES_PERMITIDOS[cambio["estado"]]}},
        {"$set": nuevo},
        return_document=ReturnDocument.AFTER,
    )
    if actualizado:
        return actualizado, None
    return None, await coleccion.find_one({"_id": vehiculo_id})


async def conteo_por_localidad(coleccion: AsyncCollection) -> dict[str, dict[str, int]]:
    """{codigo_localidad: {estado: cantidad}} para los vehículos que tienen localidad."""
    pipeline = [
        {"$match": {"localidad": {"$exists": True}}},
        {"$group": {"_id": {"loc": "$localidad.codigo", "estado": "$estado"}, "n": {"$sum": 1}}},
    ]
    cursor = await coleccion.aggregate(pipeline)
    conteo: dict[str, dict[str, int]] = {}
    async for fila in cursor:
        conteo.setdefault(fila["_id"]["loc"], {})[fila["_id"]["estado"]] = fila["n"]
    return conteo


async def rellenar_localidades(coleccion: AsyncCollection, localidades: AsyncCollection) -> int:
    """Asigna localidad a vehículos guardados antes de existir ese campo. Devuelve cuántos actualizó."""
    from app.db.localidades import buscar_por_punto, referencia

    actualizados = 0
    async for doc in coleccion.find({"localidad": {"$exists": False}}):
        lng, lat = doc["ubicacion"]["coordinates"]
        loc = await buscar_por_punto(localidades, lng, lat)
        if loc:
            await coleccion.update_one({"_id": doc["_id"]}, {"$set": {"localidad": referencia(loc)}})
            actualizados += 1
    return actualizados
