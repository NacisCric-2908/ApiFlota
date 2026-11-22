from typing import Literal

from pydantic import BaseModel, Field


class LocalidadRef(BaseModel):
    codigo: str = Field(description="Código oficial de la localidad ('01' a '20').", examples=["17"])
    nombre: str = Field(examples=["La Candelaria"])


class ConteoVehiculos(BaseModel):
    total: int
    disponible: int
    en_viaje: int
    mantenimiento: int


class LocalidadResumen(LocalidadRef):
    areaM2: int
    vehiculos: ConteoVehiculos


class VerificacionLocalidad(BaseModel):
    dentroDeBogota: bool
    localidad: LocalidadRef | None = None


class PropiedadesLocalidad(LocalidadRef):
    areaM2: int


class LocalidadGeo(BaseModel):
    """Localidad como Feature GeoJSON (geometría MultiPolygon, coordenadas [longitud, latitud])."""

    type: Literal["Feature"] = "Feature"
    properties: PropiedadesLocalidad
    geometry: dict
