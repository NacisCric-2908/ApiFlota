"""Llamadas a terceros con tiempo máximo, reintentos limitados y un único tipo de error."""

import asyncio
from collections.abc import Awaitable, Callable

import httpx


class ServicioExternoError(Exception):
    """El tercero no respondió bien. `motivo` es corto y seguro de mostrar (sin datos internos)."""

    def __init__(self, servicio: str, motivo: str):
        super().__init__(f"{servicio}: {motivo}")
        self.servicio = servicio
        self.motivo = motivo


async def get_json(
    http: httpx.AsyncClient,
    servicio: str,
    url: str,
    *,
    params: dict,
    reintentos: int,
    backoff_s: float,
    antes_de_cada_intento: Callable[[], Awaitable[None]] | None = None,
) -> dict:
    """GET que devuelve JSON. Reintenta solo lo transitorio: cortes de red, timeouts, 429 y 5xx.

    Un 4xx distinto de 429 es un error nuestro: no se reintenta. El tiempo máximo por intento lo
    fija el cliente httpx; la espera entre intentos se duplica (backoff exponencial).
    """
    motivo = "desconocido"
    for intento in range(reintentos + 1):
        if antes_de_cada_intento:
            await antes_de_cada_intento()  # p. ej. respetar el límite de peticiones por segundo
        try:
            r = await http.get(url, params=params)
        except httpx.TransportError as e:  # incluye timeouts y fallos de conexión
            motivo = type(e).__name__
        else:
            if r.status_code == 200:
                try:
                    return r.json()
                except ValueError:
                    raise ServicioExternoError(servicio, "respuesta_no_json") from None
            if r.status_code != 429 and r.status_code < 500:
                raise ServicioExternoError(servicio, f"http_{r.status_code}")
            motivo = f"http_{r.status_code}"
        if intento < reintentos:
            await asyncio.sleep(backoff_s * 2**intento)
    raise ServicioExternoError(servicio, motivo)
