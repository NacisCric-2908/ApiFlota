"""Caché en memoria con vencimiento, que además sirve datos viejos si el tercero falla."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Entrada:
    valor: Any
    fresco: bool  # False: pasó el TTL pero sigue siendo usable como respaldo si el tercero falla


class CacheTTL:
    def __init__(
        self,
        ttl_s: float,
        max_antiguedad_s: float,
        max_items: int = 1000,
        reloj: Callable[[], float] = time.monotonic,
    ):
        self.ttl_s = ttl_s
        self.max_antiguedad_s = max_antiguedad_s
        self.max_items = max_items
        self._reloj = reloj
        self._datos: dict[Any, tuple[float, Any]] = {}

    def get(self, clave: Any) -> Entrada | None:
        guardado = self._datos.get(clave)
        if guardado is None:
            return None
        edad = self._reloj() - guardado[0]
        if edad > self.max_antiguedad_s:
            del self._datos[clave]
            return None
        return Entrada(valor=guardado[1], fresco=edad <= self.ttl_s)

    def set(self, clave: Any, valor: Any) -> None:
        self._datos.pop(clave, None)
        self._datos[clave] = (self._reloj(), valor)
        while len(self._datos) > self.max_items:
            self._datos.pop(next(iter(self._datos)))  # descarta el más antiguo

    def __len__(self) -> int:
        return len(self._datos)
