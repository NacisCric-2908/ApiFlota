from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, Security
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError

from app.core.alcances import (
    VEHICULOS_ESCRIBIR,
    VEHICULOS_LEER,
    cabecera_gateway,
    oauth2,
)
from app.core.errors import ApiError
from app.db import vehiculos as repo
from app.db.localidades import buscar_por_punto, referencia, slug
from app.db.mongo import obtener_coleccion, obtener_localidades
from app.schemas.error import ErrorRespuesta
from app.schemas.vehiculo import (
    CambioEstado,
    Estado,
    PaginaVehiculos,
    Punto,
    Tipo,
    VehiculoCrear,
    VehiculoReemplazar,
    VehiculoSalida,
)

router = APIRouter(
    prefix="/vehiculos",
    tags=["Vehiculos"],
    dependencies=[Security(cabecera_gateway)],
    responses={
        401: {"model": ErrorRespuesta, "description": "Falta la cabecera secreta del gateway"},
        500: {"model": ErrorRespuesta, "description": "Error interno"},
    },
)


def leer():
    return Security(oauth2, scopes=[VEHICULOS_LEER])


def escribir():
    return Security(oauth2, scopes=[VEHICULOS_ESCRIBIR])

Coleccion = Annotated[AsyncCollection, Depends(obtener_coleccion)]
Localidades = Annotated[AsyncCollection, Depends(obtener_localidades)]

E400 = {400: {"model": ErrorRespuesta, "description": "Datos o parámetros inválidos"}}
E404 = {404: {"model": ErrorRespuesta, "description": "Vehículo no encontrado"}}
E409 = {409: {"model": ErrorRespuesta, "description": "Conflicto de estado"}}


async def resolver_localidad(localidades: AsyncCollection, punto: Punto) -> dict:
    """El servicio está cerrado a Bogotá D.C.: una ubicación fuera de sus 20 localidades se rechaza."""
    lng, lat = punto.coordinates
    loc = await buscar_por_punto(localidades, lng, lat)
    if loc is None:
        raise ApiError(
            400,
            "fuera_de_bogota",
            "La ubicación está fuera de Bogotá D.C.",
            {"lat": lat, "lng": lng},
        )
    return referencia(loc)


def _no_encontrado(vehiculo_id: str) -> ApiError:
    return ApiError(404, "vehiculo_no_encontrado", f"No existe el vehículo '{vehiculo_id}'.")


@router.get(
    "/{vehiculo_id}",
    operation_id="obtenerVehiculo",
    dependencies=[leer()],
    response_model=VehiculoSalida,
    response_model_exclude_none=True,
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
    operation_id="crearVehiculo",
    dependencies=[escribir()],
    response_model=VehiculoSalida,
    response_model_exclude_none=True,
    status_code=201,
    summary="Crear un vehículo",
    responses={**E400, 409: {"model": ErrorRespuesta, "description": "El id ya existe"}},
)
async def crear(
    datos: VehiculoCrear, respuesta: Response, coleccion: Coleccion, localidades: Localidades
):
    localidad = await resolver_localidad(localidades, datos.ubicacion)
    try:
        doc = await repo.crear(coleccion, {**datos.model_dump(), "localidad": localidad})
    except DuplicateKeyError:
        raise ApiError(409, "vehiculo_duplicado", f"Ya existe el vehículo '{datos.id}'.") from None
    respuesta.headers["Location"] = f"/vehiculos/{doc['_id']}"
    return repo.a_salida(doc)


@router.put(
    "/{vehiculo_id}",
    operation_id="reemplazarVehiculo",
    dependencies=[escribir()],
    response_model=VehiculoSalida,
    response_model_exclude_none=True,
    summary="Reemplazar un vehículo",
    responses={**E400, **E404},
)
async def reemplazar(
    vehiculo_id: str, datos: VehiculoReemplazar, coleccion: Coleccion, localidades: Localidades
):
    localidad = await resolver_localidad(localidades, datos.ubicacion)
    doc = await repo.reemplazar(coleccion, vehiculo_id, {**datos.model_dump(), "localidad": localidad})
    if doc is None:
        raise _no_encontrado(vehiculo_id)
    return repo.a_salida(doc)


@router.delete(
    "/{vehiculo_id}",
    operation_id="eliminarVehiculo",
    dependencies=[escribir()],
    status_code=204,
    summary="Eliminar un vehículo (no permitido si está en viaje)",
    responses={**E404, 409: {"model": ErrorRespuesta, "description": "El vehículo está en viaje"}},
)
async def eliminar(vehiculo_id: str, coleccion: Coleccion):
    resultado = await repo.eliminar(coleccion, vehiculo_id)
    if resultado == "no_existe":
        raise _no_encontrado(vehiculo_id)
    if resultado == "en_viaje":
        raise ApiError(409, "vehiculo_en_viaje", "No se puede eliminar un vehículo que está en viaje.")
    return Response(status_code=204)


@router.patch(
    "/{vehiculo_id}/estado",
    operation_id="cambiarEstadoVehiculo",
    dependencies=[escribir()],
    response_model=VehiculoSalida,
    response_model_exclude_none=True,
    summary="Cambiar el estado (y opcionalmente ubicación y batería) de forma atómica",
    description=(
        "Transiciones válidas: `disponible`→`en_viaje`|`mantenimiento`, "
        "`en_viaje`→`disponible`|`mantenimiento`, `mantenimiento`→`disponible`. "
        "Repetir el estado actual responde 409. Si dos peticiones compiten por el mismo "
        "vehículo, solo una gana."
    ),
    responses={**E400, **E404, **E409},
)
async def cambiar_estado(
    vehiculo_id: str, cambio: CambioEstado, coleccion: Coleccion, localidades: Localidades
):
    datos = cambio.model_dump(exclude_none=True)
    if cambio.ubicacion:  # si se mueve, hay que recalcular la localidad (y debe seguir en Bogotá)
        datos["localidad"] = await resolver_localidad(localidades, cambio.ubicacion)
    actualizado, actual = await repo.cambiar_estado(coleccion, vehiculo_id, datos)
    if actualizado:
        return repo.a_salida(actualizado)
    if actual is None:
        raise _no_encontrado(vehiculo_id)
    raise ApiError(
        409,
        "transicion_invalida",
        f"No se puede pasar de '{actual['estado']}' a '{cambio.estado}'.",
        {"estadoActual": actual["estado"], "estadoSolicitado": cambio.estado},
    )


@router.get(
    "",
    operation_id="listarVehiculos",
    dependencies=[leer()],
    response_model=PaginaVehiculos,
    response_model_exclude_none=True,
    summary="Listar vehículos con filtros, cercanía y paginación",
    description=(
        "Filtros: `tipo`, `estado`, `localidad`, `bateriaMin`. Cercanía: `lat` y `lng` van juntas; "
        "`radioMetros` (500 por defecto) solo se acepta con ellas. Con cercanía, el resultado "
        "va del más cercano al más lejano e incluye `distanciaMetros`."
    ),
    responses={**E400},
)
async def listar(
    coleccion: Coleccion,
    tipo: Tipo | None = None,
    estado: Estado | None = None,
    localidad: Annotated[
        str | None,
        Query(description="Código ('17') o nombre ('La Candelaria', 'usaquen'). No distingue tildes ni mayúsculas."),
    ] = None,
    bateriaMin: Annotated[int | None, Query(ge=0, le=100)] = None,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180)] = None,
    radioMetros: Annotated[float | None, Query(gt=0, le=50_000)] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 20,
):
    if (lat is None) != (lng is None):
        raise ApiError(400, "busqueda_geo_incompleta", "Los parámetros 'lat' y 'lng' van juntos.")
    if radioMetros is not None and lat is None:
        raise ApiError(400, "busqueda_geo_incompleta", "'radioMetros' requiere 'lat' y 'lng'.")

    filtro: dict = {}
    if tipo:
        filtro["tipo"] = tipo
    if estado:
        filtro["estado"] = estado
    if bateriaMin is not None:
        filtro["bateriaPct"] = {"$gte": bateriaMin}
    if localidad:
        filtro["$or"] = [{"localidad.codigo": localidad}, {"localidad.slug": slug(localidad)}]

    cerca_de = (lat, lng, radioMetros or 500.0) if lat is not None else None
    docs, total = await repo.listar(coleccion, filtro, pagina, tamano, cerca_de)
    return {"items": [repo.a_salida(d) for d in docs], "pagina": pagina, "tamano": tamano, "total": total}
