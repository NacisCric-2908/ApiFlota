"""Clima actual con Open-Meteo (https://open-meteo.com): gratuito, sin llave, 600 peticiones/min."""

from datetime import datetime, timezone

from app.externos.contenedor import Externos
from app.externos.http import ServicioExternoError, get_json

SERVICIO = "open-meteo"
CAMPOS_ACTUALES = "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m"

# Códigos WMO que implican agua cayendo: llovizna, lluvia, chubascos y tormentas.
CODIGOS_LLUVIA = {*range(51, 58), *range(61, 68), *range(80, 83), *range(95, 100)}
DESCRIPCIONES = {
    0: "Despejado", 1: "Mayormente despejado", 2: "Parcialmente nublado", 3: "Nublado",
    45: "Niebla", 48: "Niebla con escarcha",
    51: "Llovizna leve", 53: "Llovizna moderada", 55: "Llovizna intensa",
    56: "Llovizna helada leve", 57: "Llovizna helada intensa",
    61: "Lluvia leve", 63: "Lluvia moderada", 65: "Lluvia intensa",
    66: "Lluvia helada leve", 67: "Lluvia helada intensa",
    71: "Nevada leve", 73: "Nevada moderada", 75: "Nevada intensa", 77: "Granos de nieve",
    80: "Chubascos leves", 81: "Chubascos moderados", 82: "Chubascos violentos",
    85: "Chubascos de nieve leves", 86: "Chubascos de nieve intensos",
    95: "Tormenta", 96: "Tormenta con granizo leve", 99: "Tormenta con granizo intenso",
}  # fmt: skip


def interpretar(datos: dict) -> dict:
    try:
        actual = datos["current"]
        codigo = int(actual["weather_code"])
        precipitacion = float(actual["precipitation"])
        return {
            "temperaturaC": float(actual["temperature_2m"]),
            "humedadPct": actual.get("relative_humidity_2m"),
            "precipitacionMm": precipitacion,
            "lluvia": precipitacion > 0 or codigo in CODIGOS_LLUVIA,
            "vientoKmh": float(actual["wind_speed_10m"]),
            "codigoClima": codigo,
            "descripcion": DESCRIPCIONES.get(codigo, "Sin descripción"),
            # Se pide la hora en UTC (timezone=UTC), así que no hay que adivinar la zona.
            "observadoEn": datetime.fromisoformat(actual["time"]).replace(tzinfo=timezone.utc),
        }
    except (KeyError, TypeError, ValueError):
        raise ServicioExternoError(SERVICIO, "respuesta_inesperada") from None


async def obtener_clima(ext: Externos, lat: float, lng: float) -> tuple[dict, str]:
    """Devuelve (clima, origen). Origen: 'externo', 'cache' o 'cache_desactualizada'.

    Plan de degradación: si Open-Meteo falla se sirve el último dato guardado (hasta 3 h) marcado
    como desactualizado; si no hay ninguno, lanza ServicioExternoError (el router responde 503).
    """
    # Redondear a 2 decimales (~1 km) aumenta los aciertos de caché: el clima no cambia en 100 m.
    clave = (round(lat, 2), round(lng, 2))
    guardado = ext.cache_clima.get(clave)
    if guardado and guardado.fresco:
        return guardado.valor, "cache"

    try:
        datos = await get_json(
            ext.http,
            SERVICIO,
            ext.settings.open_meteo_url,
            params={
                "latitude": lat,
                "longitude": lng,
                "current": CAMPOS_ACTUALES,
                "timezone": "UTC",
            },
            reintentos=ext.settings.externos_reintentos,
            backoff_s=ext.settings.externos_backoff_s,
        )
        clima = interpretar(datos)
    except ServicioExternoError:
        if guardado:
            return guardado.valor, "cache_desactualizada"
        raise

    ext.cache_clima.set(clave, clima)
    return clima, "externo"
