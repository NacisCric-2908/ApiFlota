"""Reemplazo de las APIs de terceros: en las pruebas nada sale a internet."""

import time

import httpx

HOST_CLIMA = "api.open-meteo.com"
HOST_DIRECCION = "nominatim.openstreetmap.org"

CLIMA_OK = {
    "latitude": 4.745,
    "longitude": -74.1,
    "current": {
        "time": "2026-11-22T14:30",
        "interval": 900,
        "temperature_2m": 19.6,
        "relative_humidity_2m": 61,
        "precipitation": 0.0,
        "weather_code": 2,
        "wind_speed_10m": 1.7,
    },
}
DIRECCION_OK = {
    "display_name": "Carrera 70F, Campania, Localidad Suba, Bogotá, Colombia",
    "address": {
        "road": "Carrera 70F",
        "neighbourhood": "Campania",
        "suburb": "Localidad Suba",
        "postcode": "111121",
    },
}


def clima_con(**actual):
    return {**CLIMA_OK, "current": {**CLIMA_OK["current"], **actual}}


class Simulador:
    """Cada tercero se controla con una función `peticion -> httpx.Response` (o que lance un error)."""

    def __init__(self):
        self.peticiones: list[httpx.Request] = []
        self.instantes: list[float] = []
        self.clima = lambda _: httpx.Response(200, json=CLIMA_OK)
        self.direccion = lambda _: httpx.Response(200, json=DIRECCION_OK)

    def __call__(self, peticion: httpx.Request) -> httpx.Response:
        self.peticiones.append(peticion)
        self.instantes.append(time.monotonic())
        if peticion.url.host == HOST_CLIMA:
            return self.clima(peticion)
        if peticion.url.host == HOST_DIRECCION:
            return self.direccion(peticion)
        raise AssertionError(f"Llamada inesperada a un host no simulado: {peticion.url}")

    def llamadas(self, host: str) -> list[httpx.Request]:
        return [p for p in self.peticiones if p.url.host == host]


def fallar(estado: int):
    return lambda _: httpx.Response(estado)


def lanzar(error: Exception):
    def _lanzar(_):
        raise error

    return _lanzar


def tras_fallos(fallos: int, estado: int, respuesta: httpx.Response):
    """Falla `fallos` veces con `estado` y luego responde `respuesta`."""
    cuenta = {"n": 0}

    def _responder(_):
        cuenta["n"] += 1
        return httpx.Response(estado) if cuenta["n"] <= fallos else respuesta

    return _responder


class Reloj:
    """Reloj manual para probar vencimientos de caché sin esperar."""

    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t
