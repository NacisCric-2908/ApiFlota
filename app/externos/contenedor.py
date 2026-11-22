"""Estado compartido de las integraciones: un solo cliente HTTP, cachés y control de tasa."""

import asyncio

import httpx
from fastapi import Request

from app.core.config import Settings
from app.externos.cache import CacheTTL


class Externos:
    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None):
        self.settings = settings
        self.http = http or httpx.AsyncClient(
            timeout=httpx.Timeout(settings.externos_timeout_s),
            headers={"User-Agent": settings.externos_user_agent},
        )
        # El clima se actualiza cada 15 min: 10 min de caché; como respaldo sirve hasta 3 h.
        self.cache_clima = CacheTTL(ttl_s=10 * 60, max_antiguedad_s=3 * 3600)
        # Las direcciones casi no cambian: 24 h de caché; como respaldo sirve hasta 7 días.
        self.cache_direccion = CacheTTL(ttl_s=24 * 3600, max_antiguedad_s=7 * 24 * 3600)
        self.turno_nominatim = asyncio.Lock()
        self.ultimo_nominatim = 0.0

    async def cerrar(self) -> None:
        await self.http.aclose()


def obtener_externos(request: Request) -> Externos:
    return request.app.state.externos
