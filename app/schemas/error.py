from typing import Any

from pydantic import BaseModel


class ErrorRespuesta(BaseModel):
    """Formato de error común a todos los servicios del clúster."""

    codigo: str
    mensaje: str
    detalle: Any = {}
