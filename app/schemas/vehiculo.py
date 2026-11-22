from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.localidad import LocalidadRef

Tipo = Literal["scooter", "bicicleta"]
Estado = Literal["disponible", "en_viaje", "mantenimiento"]

Bateria = Annotated[int, Field(ge=0, le=100, description="Porcentaje de batería (0 a 100).")]


class Punto(BaseModel):
    """Punto GeoJSON. Ojo: el orden de las coordenadas es [longitud, latitud]."""

    type: Literal["Point"] = "Point"
    coordinates: Annotated[list[float], Field(min_length=2, max_length=2)]

    @field_validator("coordinates")
    @classmethod
    def validar_rango(cls, valor: list[float]) -> list[float]:
        lng, lat = valor
        if not (-180 <= lng <= 180 and -90 <= lat <= 90):
            raise ValueError("Coordenadas fuera de rango: se espera [longitud, latitud].")
        return valor


class VehiculoBase(BaseModel):
    tipo: Tipo
    bateriaPct: Bateria
    estado: Estado
    ubicacion: Punto


class VehiculoCrear(VehiculoBase):
    id: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9_-]{1,40}$",
        description="Opcional. Si se omite, el servicio genera uno (veh-XXXXXXXX).",
    )


class VehiculoReemplazar(VehiculoBase):
    pass


class VehiculoSalida(VehiculoBase):
    id: str
    localidad: LocalidadRef | None = Field(
        default=None,
        description="Localidad de Bogotá donde está el vehículo (la calcula el servicio a partir de la ubicación).",
    )
    actualizadoEn: datetime
    distanciaMetros: float | None = Field(
        default=None, description="Solo aparece en búsquedas por cercanía."
    )


class CambioEstado(BaseModel):
    estado: Estado
    ubicacion: Punto | None = None
    bateriaPct: Bateria | None = None


class PaginaVehiculos(BaseModel):
    items: list[VehiculoSalida]
    pagina: int
    tamano: int
    total: int
