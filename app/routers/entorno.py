"""Entorno de un vehículo con datos de APIs de terceros: clima y dirección."""

from typing import Annotated

from fastapi import APIRouter, Depends, Security
from pymongo.asynchronous.collection import AsyncCollection

from app.core.alcances import VEHICULOS_LEER, cabecera_gateway, oauth2
from app.core.errors import ApiError
from app.db import vehiculos as repo
from app.db.mongo import obtener_coleccion
from app.externos.clima import obtener_clima
from app.externos.contenedor import Externos, obtener_externos
from app.externos.direccion import obtener_direccion
from app.externos.http import ServicioExternoError
from app.schemas.error import ErrorRespuesta
from app.schemas.externos import ClimaSalida, DireccionSalida

router = APIRouter(
    prefix="/vehiculos",
    tags=["Entorno del vehículo (APIs de terceros)"],
    dependencies=[Security(cabecera_gateway), Security(oauth2, scopes=[VEHICULOS_LEER])],
    responses={
        401: {"model": ErrorRespuesta, "description": "Falta la cabecera secreta del gateway"},
        404: {"model": ErrorRespuesta, "description": "Vehículo no encontrado"},
        500: {"model": ErrorRespuesta, "description": "Error interno"},
    },
)

Coleccion = Annotated[AsyncCollection, Depends(obtener_coleccion)]
ExternosDep = Annotated[Externos, Depends(obtener_externos)]


async def _vehiculo(coleccion: AsyncCollection, vehiculo_id: str) -> dict:
    doc = await repo.obtener(coleccion, vehiculo_id)
    if doc is None:
        raise ApiError(404, "vehiculo_no_encontrado", f"No existe el vehículo '{vehiculo_id}'.")
    return doc


@router.get(
    "/{vehiculo_id}/clima",
    response_model=ClimaSalida,
    summary="Clima actual en la ubicación del vehículo (Open-Meteo)",
    description=(
        "Consulta Open-Meteo con tiempo máximo de 3 s y hasta 2 reintentos; guarda el resultado "
        "10 min. **Plan de degradación:** si Open-Meteo no responde se devuelve el último dato "
        "guardado (hasta 3 h) con `origen: cache_desactualizada`; si no hay ninguno, 503 "
        "`servicio_externo_no_disponible`."
    ),
    responses={
        503: {"model": ErrorRespuesta, "description": "Open-Meteo no responde y no hay dato guardado"}
    },
)
async def clima(vehiculo_id: str, coleccion: Coleccion, externos: ExternosDep):
    doc = await _vehiculo(coleccion, vehiculo_id)
    lng, lat = doc["ubicacion"]["coordinates"]
    try:
        datos, origen = await obtener_clima(externos, lat, lng)
    except ServicioExternoError as e:
        raise ApiError(
            503,
            "servicio_externo_no_disponible",
            "No se pudo consultar el clima.",
            {"servicio": e.servicio, "motivo": e.motivo},
        ) from None
    return {**datos, "origen": origen}


@router.get(
    "/{vehiculo_id}/direccion",
    response_model=DireccionSalida,
    summary="Dirección de la ubicación del vehículo (Nominatim / OpenStreetMap)",
    description=(
        "Geocodificación inversa con tiempo máximo de 3 s, hasta 2 reintentos y no más de 1 "
        "petición por segundo (política de Nominatim); guarda el resultado 24 h. **Plan de "
        "degradación:** si Nominatim falla se devuelve el último dato guardado (hasta 7 días, "
        "`origen: cache_desactualizada`) y, si no hay, la localidad del vehículo calculada con "
        "datos propios (`origen: local`, solo `direccion` y `fuente`). Solo da 503 si el vehículo "
        "tampoco tiene localidad."
    ),
    responses={
        503: {"model": ErrorRespuesta, "description": "Nominatim no responde y no hay plan alterno"}
    },
)
async def direccion(vehiculo_id: str, coleccion: Coleccion, externos: ExternosDep):
    doc = await _vehiculo(coleccion, vehiculo_id)
    lng, lat = doc["ubicacion"]["coordinates"]
    try:
        datos, origen = await obtener_direccion(externos, lat, lng)
    except ServicioExternoError as e:
        if not doc.get("localidad"):
            raise ApiError(
                503,
                "servicio_externo_no_disponible",
                "No se pudo consultar la dirección.",
                {"servicio": e.servicio, "motivo": e.motivo},
            ) from None
        return {
            "direccion": f"{doc['localidad']['nombre']}, Bogotá D.C.",
            "fuente": "Localidades de Bogotá (Datos Abiertos Bogotá)",
            "origen": "local",
        }
    return {**datos, "origen": origen}
