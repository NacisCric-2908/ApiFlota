import asyncio
from datetime import datetime, timezone

import httpx
import pytest

from tests.simulador import DIRECCION_OK, HOST_DIRECCION, Reloj, fallar, lanzar, tras_fallos


def en(lat, lng):
    return {"ubicacion": {"type": "Point", "coordinates": [lng, lat]}}


async def test_devuelve_la_direccion_de_la_ubicacion_del_vehiculo(cliente, crear_vehiculo, terceros):
    await crear_vehiculo(id="v1")
    r = await cliente.get("/vehiculos/v1/direccion")
    assert r.status_code == 200
    assert r.json() == {
        "direccion": "Carrera 70F, Campania, Localidad Suba, Bogotá, Colombia",
        "calle": "Carrera 70F",
        "barrio": "Campania",
        "codigoPostal": "111121",
        "fuente": "OpenStreetMap Nominatim",
        "origen": "externo",
    }
    (peticion,) = terceros.llamadas(HOST_DIRECCION)
    params = peticion.url.params
    assert (params["lat"], params["lon"]) == ("4.711", "-74.0721")
    assert params["format"] == "jsonv2" and params["accept-language"] == "es"
    assert peticion.headers["user-agent"].startswith("ApiFlota")  # exigido por la política de Nominatim


async def test_la_segunda_consulta_sale_de_la_cache(cliente, crear_vehiculo, terceros):
    await crear_vehiculo(id="v1")
    assert (await cliente.get("/vehiculos/v1/direccion")).json()["origen"] == "externo"
    assert (await cliente.get("/vehiculos/v1/direccion")).json()["origen"] == "cache"
    assert len(terceros.llamadas(HOST_DIRECCION)) == 1


async def test_vehiculo_inexistente_responde_404_sin_llamar_al_tercero(cliente, terceros):
    assert (await cliente.get("/vehiculos/no-existe/direccion")).status_code == 404
    assert terceros.peticiones == []


async def test_reintenta_los_fallos_transitorios_y_se_recupera(cliente, crear_vehiculo, terceros):
    await crear_vehiculo(id="v1")
    terceros.direccion = tras_fallos(2, 503, httpx.Response(200, json=DIRECCION_OK))
    r = await cliente.get("/vehiculos/v1/direccion")
    assert r.status_code == 200 and r.json()["origen"] == "externo"
    assert len(terceros.llamadas(HOST_DIRECCION)) == 3


FALLAS = {
    "error_503": fallar(503),
    "timeout": lanzar(httpx.ConnectTimeout("lento")),
    "sin_conexion": lanzar(httpx.ConnectError("caído")),
    "bloqueo_por_uso_excesivo": fallar(429),
}


@pytest.mark.parametrize("falla", FALLAS.values(), ids=FALLAS.keys())
async def test_si_nominatim_falla_se_usa_la_localidad_como_plan_alterno(
    cliente, crear_vehiculo, terceros, externos, falla
):
    v = await crear_vehiculo(id="v1")
    terceros.direccion = falla
    r = await cliente.get("/vehiculos/v1/direccion")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["origen"] == "local"
    assert cuerpo["direccion"] == f"{v['localidad']['nombre']}, Bogotá D.C."
    assert cuerpo["calle"] is None and cuerpo["fuente"].startswith("Localidades de Bogotá")
    assert len(terceros.llamadas(HOST_DIRECCION)) == externos.settings.externos_reintentos + 1


async def test_un_punto_sin_resultado_usa_el_plan_alterno_sin_reintentar(cliente, crear_vehiculo, terceros):
    await crear_vehiculo(id="v1")
    terceros.direccion = lambda _: httpx.Response(200, json={"error": "Unable to geocode"})
    r = await cliente.get("/vehiculos/v1/direccion")
    assert r.status_code == 200 and r.json()["origen"] == "local"
    assert len(terceros.llamadas(HOST_DIRECCION)) == 1


async def test_respuesta_malformada_usa_el_plan_alterno(cliente, crear_vehiculo, terceros):
    await crear_vehiculo(id="v1")
    terceros.direccion = lambda _: httpx.Response(200, json={"address": {}})
    assert (await cliente.get("/vehiculos/v1/direccion")).json()["origen"] == "local"


async def test_sirve_el_ultimo_dato_guardado_si_el_tercero_cae(cliente, crear_vehiculo, terceros, externos):
    reloj = Reloj()
    externos.cache_direccion._reloj = reloj
    await crear_vehiculo(id="v1")
    await cliente.get("/vehiculos/v1/direccion")

    terceros.direccion = fallar(503)
    reloj.t += 25 * 3600  # vencido (TTL 24 h) pero dentro de los 7 días de respaldo
    r = await cliente.get("/vehiculos/v1/direccion")
    assert r.json()["origen"] == "cache_desactualizada"
    assert r.json()["calle"] == "Carrera 70F"

    reloj.t += 7 * 24 * 3600  # sin respaldo: cae al plan local
    assert (await cliente.get("/vehiculos/v1/direccion")).json()["origen"] == "local"


async def test_sin_localidad_y_sin_tercero_responde_503(cliente, coleccion, terceros):
    await coleccion.insert_one(
        {
            "_id": "viejo",
            "tipo": "scooter",
            "bateriaPct": 50,
            "estado": "disponible",
            "ubicacion": {"type": "Point", "coordinates": [-74.0721, 4.7110]},
            "actualizadoEn": datetime.now(timezone.utc),
        }
    )
    terceros.direccion = fallar(503)
    r = await cliente.get("/vehiculos/viejo/direccion")
    assert r.status_code == 503
    assert r.json()["detalle"]["servicio"] == "nominatim"


async def test_respeta_el_limite_de_una_peticion_por_segundo(
    cliente, crear_vehiculo, terceros, externos, monkeypatch
):
    monkeypatch.setattr(externos.settings, "nominatim_intervalo_s", 0.3)
    await crear_vehiculo(id="v1", **en(4.7110, -74.0721))
    await crear_vehiculo(id="v2", **en(4.6000, -74.0700))  # distinto punto: no sale de la caché
    await crear_vehiculo(id="v3", **en(4.6500, -74.1000))
    await asyncio.gather(*[cliente.get(f"/vehiculos/{v}/direccion") for v in ("v1", "v2", "v3")])
    t = terceros.instantes
    assert len(t) == 3
    assert min(b - a for a, b in zip(t, t[1:])) >= 0.28


async def test_los_reintentos_tambien_respetan_el_limite(cliente, crear_vehiculo, terceros, externos, monkeypatch):
    monkeypatch.setattr(externos.settings, "nominatim_intervalo_s", 0.2)
    await crear_vehiculo(id="v1")
    terceros.direccion = fallar(503)
    await cliente.get("/vehiculos/v1/direccion")
    t = terceros.instantes
    assert len(t) == 3 and min(b - a for a, b in zip(t, t[1:])) >= 0.18
