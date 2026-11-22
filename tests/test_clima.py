import httpx
import pytest

from tests.simulador import CLIMA_OK, HOST_CLIMA, Reloj, clima_con, fallar, lanzar, tras_fallos


def en(lat, lng):
    return {"ubicacion": {"type": "Point", "coordinates": [lng, lat]}}


async def test_devuelve_el_clima_de_la_ubicacion_del_vehiculo(cliente, crear_vehiculo, terceros):
    await crear_vehiculo(id="v1")
    r = await cliente.get("/vehiculos/v1/clima")
    assert r.status_code == 200
    assert r.json() == {
        "temperaturaC": 19.6,
        "humedadPct": 61,
        "precipitacionMm": 0.0,
        "lluvia": False,
        "vientoKmh": 1.7,
        "codigoClima": 2,
        "descripcion": "Parcialmente nublado",
        "observadoEn": "2026-11-22T14:30:00Z",
        "fuente": "Open-Meteo",
        "origen": "externo",
    }
    (peticion,) = terceros.llamadas(HOST_CLIMA)
    assert peticion.url.params["latitude"] == "4.711"
    assert peticion.url.params["longitude"] == "-74.0721"
    assert peticion.url.params["timezone"] == "UTC"
    assert peticion.headers["user-agent"].startswith("ApiFlota")


@pytest.mark.parametrize(
    ("actual", "lluvia"),
    [
        ({"weather_code": 0}, False),
        ({"weather_code": 3}, False),
        ({"weather_code": 61}, True),
        ({"weather_code": 80}, True),
        ({"weather_code": 95}, True),
        ({"weather_code": 3, "precipitation": 0.4}, True),
    ],
)
async def test_detecta_si_esta_lloviendo(cliente, crear_vehiculo, terceros, actual, lluvia):
    await crear_vehiculo(id="v1")
    terceros.clima = lambda _: httpx.Response(200, json=clima_con(**actual))
    assert (await cliente.get("/vehiculos/v1/clima")).json()["lluvia"] is lluvia


async def test_la_segunda_consulta_sale_de_la_cache(cliente, crear_vehiculo, terceros):
    await crear_vehiculo(id="v1")
    primera = (await cliente.get("/vehiculos/v1/clima")).json()
    segunda = (await cliente.get("/vehiculos/v1/clima")).json()
    assert (primera["origen"], segunda["origen"]) == ("externo", "cache")
    assert {**primera, "origen": ""} == {**segunda, "origen": ""}
    assert len(terceros.llamadas(HOST_CLIMA)) == 1


async def test_vehiculos_muy_cercanos_comparten_la_cache(cliente, crear_vehiculo, terceros):
    await crear_vehiculo(id="v1", **en(4.7110, -74.0721))
    await crear_vehiculo(id="v2", **en(4.7113, -74.0724))  # ~45 m
    await crear_vehiculo(id="v3", **en(4.6000, -74.0700))  # ~12 km
    for vid in ("v1", "v2", "v3"):
        assert (await cliente.get(f"/vehiculos/{vid}/clima")).status_code == 200
    assert len(terceros.llamadas(HOST_CLIMA)) == 2


async def test_vehiculo_inexistente_responde_404_sin_llamar_al_tercero(cliente, terceros):
    r = await cliente.get("/vehiculos/no-existe/clima")
    assert r.status_code == 404
    assert terceros.peticiones == []


async def test_reintenta_los_fallos_transitorios_y_se_recupera(cliente, crear_vehiculo, terceros, externos):
    await crear_vehiculo(id="v1")
    terceros.clima = tras_fallos(externos.settings.externos_reintentos, 503, httpx.Response(200, json=CLIMA_OK))
    r = await cliente.get("/vehiculos/v1/clima")
    assert r.status_code == 200 and r.json()["origen"] == "externo"
    assert len(terceros.llamadas(HOST_CLIMA)) == externos.settings.externos_reintentos + 1


async def test_reintenta_ante_429(cliente, crear_vehiculo, terceros):
    await crear_vehiculo(id="v1")
    terceros.clima = tras_fallos(1, 429, httpx.Response(200, json=CLIMA_OK))
    assert (await cliente.get("/vehiculos/v1/clima")).status_code == 200
    assert len(terceros.llamadas(HOST_CLIMA)) == 2


FALLAS_TRANSITORIAS = {
    "error_500": (fallar(500), "http_500"),
    "error_503": (fallar(503), "http_503"),
    "timeout": (lanzar(httpx.ReadTimeout("lento")), "ReadTimeout"),
    "sin_conexion": (lanzar(httpx.ConnectError("caído")), "ConnectError"),
}


@pytest.mark.parametrize(("falla", "motivo"), FALLAS_TRANSITORIAS.values(), ids=FALLAS_TRANSITORIAS.keys())
async def test_agotados_los_reintentos_responde_503(cliente, crear_vehiculo, terceros, externos, falla, motivo):
    await crear_vehiculo(id="v1")
    terceros.clima = falla
    r = await cliente.get("/vehiculos/v1/clima")
    assert r.status_code == 503
    assert r.json()["codigo"] == "servicio_externo_no_disponible"
    assert r.json()["detalle"] == {"servicio": "open-meteo", "motivo": motivo}
    assert len(terceros.llamadas(HOST_CLIMA)) == externos.settings.externos_reintentos + 1


async def test_un_error_4xx_no_se_reintenta(cliente, crear_vehiculo, terceros):
    await crear_vehiculo(id="v1")
    terceros.clima = fallar(400)
    r = await cliente.get("/vehiculos/v1/clima")
    assert r.status_code == 503 and r.json()["detalle"]["motivo"] == "http_400"
    assert len(terceros.llamadas(HOST_CLIMA)) == 1


@pytest.mark.parametrize(
    ("respuesta", "motivo"),
    [
        (httpx.Response(200, text="<html>mantenimiento</html>"), "respuesta_no_json"),
        (httpx.Response(200, json={"current": {}}), "respuesta_inesperada"),
        (httpx.Response(200, json={}), "respuesta_inesperada"),
    ],
)
async def test_respuestas_malformadas_responden_503(cliente, crear_vehiculo, terceros, respuesta, motivo):
    await crear_vehiculo(id="v1")
    terceros.clima = lambda _: respuesta
    r = await cliente.get("/vehiculos/v1/clima")
    assert r.status_code == 503 and r.json()["detalle"]["motivo"] == motivo


async def test_un_fallo_no_se_guarda_en_cache(cliente, crear_vehiculo, terceros):
    await crear_vehiculo(id="v1")
    terceros.clima = fallar(503)
    assert (await cliente.get("/vehiculos/v1/clima")).status_code == 503
    terceros.clima = lambda _: httpx.Response(200, json=CLIMA_OK)
    r = await cliente.get("/vehiculos/v1/clima")
    assert r.status_code == 200 and r.json()["origen"] == "externo"


async def test_con_cache_fresca_no_importa_que_el_tercero_este_caido(cliente, crear_vehiculo, terceros):
    await crear_vehiculo(id="v1")
    await cliente.get("/vehiculos/v1/clima")
    terceros.clima = fallar(503)
    r = await cliente.get("/vehiculos/v1/clima")
    assert r.status_code == 200 and r.json()["origen"] == "cache"
    assert len(terceros.llamadas(HOST_CLIMA)) == 1


async def test_plan_de_degradacion_sirve_el_ultimo_dato_si_el_tercero_cae(
    cliente, crear_vehiculo, terceros, externos
):
    reloj = Reloj()
    externos.cache_clima._reloj = reloj
    await crear_vehiculo(id="v1")
    await cliente.get("/vehiculos/v1/clima")  # se guarda

    terceros.clima = fallar(503)
    reloj.t += 11 * 60  # vencido (TTL 10 min) pero aún utilizable como respaldo
    r = await cliente.get("/vehiculos/v1/clima")
    assert r.status_code == 200
    assert r.json()["origen"] == "cache_desactualizada"
    assert r.json()["temperaturaC"] == 19.6

    reloj.t += 3 * 3600  # ya demasiado viejo: no hay respaldo
    assert (await cliente.get("/vehiculos/v1/clima")).status_code == 503
