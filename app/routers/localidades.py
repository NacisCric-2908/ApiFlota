from typing import Annotated

from fastapi import APIRouter, Depends, Query, Security
from pymongo.asynchronous.collection import AsyncCollection

from app.core.alcances import VEHICULOS_LEER, cabecera_gateway, oauth2
from app.core.errors import ApiError
from app.db import localidades as repo
from app.db import vehiculos as repo_vehiculos
from app.db.mongo import obtener_coleccion, obtener_localidades
from app.schemas.error import ErrorRespuesta
from app.schemas.localidad import LocalidadGeo, LocalidadResumen, VerificacionLocalidad

router = APIRouter(
    prefix="/localidades",
    tags=["Localidades"],
    dependencies=[Security(cabecera_gateway), Security(oauth2, scopes=[VEHICULOS_LEER])],
    responses={
        401: {"model": ErrorRespuesta, "description": "Falta la cabecera secreta del gateway"},
        500: {"model": ErrorRespuesta, "description": "Error interno"},
    },
)

Localidades = Annotated[AsyncCollection, Depends(obtener_localidades)]
Vehiculos = Annotated[AsyncCollection, Depends(obtener_coleccion)]

ESTADOS = ("disponible", "en_viaje", "mantenimiento")


@router.get(
    "",
    operation_id="listarLocalidades",
    response_model=list[LocalidadResumen],
    summary="Las 20 localidades de Bogotá con el conteo de vehículos de cada una",
)
async def listar(localidades: Localidades, vehiculos: Vehiculos):
    conteo = await repo_vehiculos.conteo_por_localidad(vehiculos)
    resultado = []
    for loc in await repo.listar(localidades):
        por_estado = conteo.get(loc["codigo"], {})
        resultado.append(
            {
                "codigo": loc["codigo"],
                "nombre": loc["nombre"],
                "areaM2": loc["areaM2"],
                "vehiculos": {
                    "total": sum(por_estado.values()),
                    **{estado: por_estado.get(estado, 0) for estado in ESTADOS},
                },
            }
        )
    return resultado


# Declarada antes de /{codigo} para que "verificar" no se interprete como un código.
@router.get(
    "/verificar",
    operation_id="verificarLocalidad",
    response_model=VerificacionLocalidad,
    response_model_exclude_none=False,
    summary="¿En qué localidad de Bogotá está un punto?",
    description="Siempre responde 200: fuera de Bogotá devuelve `dentroDeBogota: false` y `localidad: null`.",
    responses={400: {"model": ErrorRespuesta, "description": "Coordenadas inválidas"}},
)
async def verificar(
    localidades: Localidades,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
):
    loc = await repo.buscar_por_punto(localidades, lng, lat)
    if loc is None:
        return {"dentroDeBogota": False, "localidad": None}
    return {"dentroDeBogota": True, "localidad": {"codigo": loc["codigo"], "nombre": loc["nombre"]}}


@router.get(
    "/{codigo}",
    operation_id="obtenerLocalidad",
    response_model=LocalidadGeo,
    summary="Una localidad con su geometría (Feature GeoJSON)",
    responses={404: {"model": ErrorRespuesta, "description": "Localidad no encontrada"}},
)
async def detalle(codigo: str, localidades: Localidades):
    loc = await repo.obtener(localidades, codigo, con_geometria=True)
    if loc is None:
        raise ApiError(404, "localidad_no_encontrada", f"No existe la localidad '{codigo}'.")
    return {
        "type": "Feature",
        "properties": {"codigo": loc["codigo"], "nombre": loc["nombre"], "areaM2": loc["areaM2"]},
        "geometry": loc["geometria"],
    }
