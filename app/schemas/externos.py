from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Origen = Literal["externo", "cache", "cache_desactualizada", "local"]
DESCRIPCION_ORIGEN = (
    "De dónde salió el dato: `externo` (consulta en vivo), `cache`, `cache_desactualizada` "
    "(el tercero falló y se sirvió el último dato guardado) o `local` (plan alterno con datos propios)."
)


class ClimaSalida(BaseModel):
    temperaturaC: float
    humedadPct: int | None = None
    precipitacionMm: float
    lluvia: bool = Field(description="True si está lloviendo ahora (precipitación > 0 o código WMO de lluvia).")
    vientoKmh: float
    codigoClima: int = Field(description="Código WMO del estado del tiempo.")
    descripcion: str
    observadoEn: datetime
    fuente: str = "Open-Meteo"
    origen: Origen = Field(description=DESCRIPCION_ORIGEN)


class DireccionSalida(BaseModel):
    direccion: str
    calle: str | None = None
    barrio: str | None = None
    codigoPostal: str | None = None
    fuente: str
    origen: Origen = Field(description=DESCRIPCION_ORIGEN)
