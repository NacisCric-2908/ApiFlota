from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError

from app.core.errors import ApiError
from app.db import vehiculos as repo
from app.db.mongo import obtener_coleccion
from app.schemas.error import ErrorRespuesta
from app.schemas.vehiculo import (
    CambioEstado,
    Estado,
    PaginaVehiculos,
    Tipo,
    VehiculoCrear,
    VehiculoReemplazar,
    VehiculoSalida,
)

router = APIRouter(prefix="/vehiculos", tags=["Vehículos"])

Coleccion = Annotated[AsyncCollection, Depends(obtener_coleccion)]

E400 = {400: {"model": ErrorRespuesta, "description": "Datos o parámetros inválidos"}}
E404 = {404: {"model": ErrorRespuesta, "description": "Vehículo no encontrado"}}
E409 = {409: {"model": ErrorRespuesta, "description": "Conflicto de estado"}}


def _no_encontrado(vehiculo_id: str) -> ApiError:
    return ApiError(404, "vehiculo_no_encontrado", f"No existe el vehículo '{vehiculo_id}'.")


@router.get(
    "/{vehiculo_id}",
    response_model=VehiculoSalida,
    summary="Detalle de un vehículo",
    responses={**E404},
)
async def detalle(vehiculo_id: str, coleccion: Coleccion):
    doc = await repo.obtener(coleccion, vehiculo_id)
    if doc is None:
        raise _no_encontrado(vehiculo_id)
    return repo.a_salida(doc)


@router.post(
    "",
    response_model=VehiculoSalida,
    status_code=201,
    summary="Crear un vehículo",
    responses={**E400, 409: {"model": ErrorRespuesta, "description": "El id ya existe"}},
)
async def crear(datos: VehiculoCrear, respuesta: Response, coleccion: Coleccion):
    try:
        doc = await repo.crear(coleccion, datos.model_dump())
    except DuplicateKeyError:
        raise ApiError(409, "vehiculo_duplicado", f"Ya existe el vehículo '{datos.id}'.") from None
    respuesta.headers["Location"] = f"/vehiculos/{doc['_id']}"
    return repo.a_salida(doc)
