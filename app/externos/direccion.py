"""Geocodificación inversa con Nominatim/OpenStreetMap (https://nominatim.org).

Su política de uso (https://operations.osmfoundation.org/policies/nominatim/) exige: máximo 1
petición por segundo, un User-Agent que identifique la aplicación y guardar resultados en caché.
"""

import asyncio
import time

from app.externos.contenedor import Externos
from app.externos.http import ServicioExternoError, get_json

SERVICIO = "nominatim"
FUENTE = "OpenStreetMap Nominatim"


def interpretar(datos: dict) -> dict:
    if "error" in datos:  # Nominatim responde 200 con {"error": ...} si no hay nada en ese punto
        raise ServicioExternoError(SERVICIO, "sin_resultado")
    try:
        detalle = datos.get("address", {})
        return {
            "direccion": datos["display_name"],
            "calle": detalle.get("road"),
            "barrio": detalle.get("neighbourhood") or detalle.get("suburb"),
            "codigoPostal": detalle.get("postcode"),
            "fuente": FUENTE,
        }
    except (KeyError, TypeError):
        raise ServicioExternoError(SERVICIO, "respuesta_inesperada") from None


async def _esperar_turno(ext: Externos) -> None:
    """Espacia las peticiones salientes para no pasar de 1 por segundo (también en reintentos)."""
    async with ext.turno_nominatim:
        espera = ext.ultimo_nominatim + ext.settings.nominatim_intervalo_s - time.monotonic()
        if espera > 0:
            await asyncio.sleep(espera)
        ext.ultimo_nominatim = time.monotonic()


async def obtener_direccion(ext: Externos, lat: float, lng: float) -> tuple[dict, str]:
    """Devuelve (dirección, origen). Origen: 'externo', 'cache' o 'cache_desactualizada'.

    Si Nominatim falla y hay un dato guardado (hasta 7 días) se sirve como desactualizado; si no,
    lanza ServicioExternoError y el router cae al plan local (la localidad, con datos propios).
    """
    clave = (round(lat, 4), round(lng, 4))  # ~11 m
    guardado = ext.cache_direccion.get(clave)
    if guardado and guardado.fresco:
        return guardado.valor, "cache"

    try:
        datos = await get_json(
            ext.http,
            SERVICIO,
            ext.settings.nominatim_url,
            params={
                "lat": lat,
                "lon": lng,
                "format": "jsonv2",
                "zoom": 18,
                "addressdetails": 1,
                "accept-language": "es",
            },
            reintentos=ext.settings.externos_reintentos,
            backoff_s=ext.settings.externos_backoff_s,
            antes_de_cada_intento=lambda: _esperar_turno(ext),
        )
        direccion = interpretar(datos)
    except ServicioExternoError:
        if guardado:
            return guardado.valor, "cache_desactualizada"
        raise

    ext.cache_direccion.set(clave, direccion)
    return direccion, "externo"
