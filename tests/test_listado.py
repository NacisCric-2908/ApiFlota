import pytest

CENTRO = {"lat": 4.7110, "lng": -74.0721}


def en(lng, lat):
    return {"ubicacion": {"type": "Point", "coordinates": [lng, lat]}}


async def test_filtra_por_tipo_estado_y_bateria(cliente, crear_vehiculo):
    await crear_vehiculo(id="a", tipo="scooter", estado="disponible", bateriaPct=90)
    await crear_vehiculo(id="b", tipo="bicicleta", estado="disponible", bateriaPct=40)
    await crear_vehiculo(id="c", tipo="scooter", estado="mantenimiento", bateriaPct=20)

    ids = lambda r: sorted(v["id"] for v in r.json()["items"])  # noqa: E731
    assert ids(await cliente.get("/vehiculos", params={"tipo": "scooter"})) == ["a", "c"]
    assert ids(await cliente.get("/vehiculos", params={"estado": "disponible"})) == ["a", "b"]
    assert ids(await cliente.get("/vehiculos", params={"bateriaMin": 40})) == ["a", "b"]
    combinado = {"tipo": "scooter", "estado": "disponible", "bateriaMin": 50}
    assert ids(await cliente.get("/vehiculos", params=combinado)) == ["a"]


async def test_busqueda_por_cercania_ordena_del_mas_cercano_al_mas_lejano(cliente, crear_vehiculo):
    # ~0, ~100 m, ~200 m al este del punto (0.0009° de longitud ≈ 100 m en Bogotá) y uno a ~1 km.
    await crear_vehiculo(id="lejos2", **en(-74.0721 + 0.0018, 4.7110))
    await crear_vehiculo(id="lejos1", **en(-74.0721 + 0.0009, 4.7110))
    await crear_vehiculo(id="centro", **en(-74.0721, 4.7110))
    await crear_vehiculo(id="fuera", **en(-74.0721 + 0.009, 4.7110))

    r = await cliente.get("/vehiculos", params={**CENTRO, "radioMetros": 500})
    cuerpo = r.json()
    assert [v["id"] for v in cuerpo["items"]] == ["centro", "lejos1", "lejos2"]
    distancias = [v["distanciaMetros"] for v in cuerpo["items"]]
    assert distancias == sorted(distancias)
    assert distancias[0] < 1 and 90 < distancias[1] < 110 and 190 < distancias[2] < 210
    assert cuerpo["total"] == 3


async def test_cercania_combinada_con_filtros(cliente, crear_vehiculo):
    await crear_vehiculo(id="libre", estado="disponible", **en(-74.0721, 4.7110))
    await crear_vehiculo(id="ocupado", estado="en_viaje", **en(-74.0721, 4.7111))
    r = await cliente.get("/vehiculos", params={**CENTRO, "radioMetros": 500, "estado": "disponible"})
    assert [v["id"] for v in r.json()["items"]] == ["libre"]


async def test_radio_por_defecto_es_500_m(cliente, crear_vehiculo):
    await crear_vehiculo(id="cerca", **en(-74.0721 + 0.0027, 4.7110))  # ~300 m
    await crear_vehiculo(id="lejos", **en(-74.0721 + 0.009, 4.7110))  # ~1 km
    r = await cliente.get("/vehiculos", params=CENTRO)
    assert [v["id"] for v in r.json()["items"]] == ["cerca"]


async def test_paginacion_sin_cercania(cliente, crear_vehiculo):
    for i in range(5):
        await crear_vehiculo(id=f"v{i}")
    r = await cliente.get("/vehiculos", params={"pagina": 2, "tamano": 2})
    cuerpo = r.json()
    assert [v["id"] for v in cuerpo["items"]] == ["v2", "v3"]
    assert (cuerpo["pagina"], cuerpo["tamano"], cuerpo["total"]) == (2, 2, 5)


async def test_paginacion_con_cercania(cliente, crear_vehiculo):
    for i in range(5):
        await crear_vehiculo(id=f"v{i}", **en(-74.0721 + i * 0.0003, 4.7110))
    r = await cliente.get("/vehiculos", params={**CENTRO, "pagina": 2, "tamano": 2})
    cuerpo = r.json()
    assert [v["id"] for v in cuerpo["items"]] == ["v2", "v3"]
    assert cuerpo["total"] == 5


async def test_pagina_vacia_si_se_pasa_del_final(cliente, crear_vehiculo):
    await crear_vehiculo(id="unico")
    r = await cliente.get("/vehiculos", params={"pagina": 9})
    assert r.status_code == 200
    assert r.json()["items"] == [] and r.json()["total"] == 1


PARAMETROS_INVALIDOS = {
    "lat_sin_lng": {"lat": 4.7},
    "lng_sin_lat": {"lng": -74.0},
    "radio_sin_punto": {"radioMetros": 100},
    "latitud_fuera_de_rango": {"lat": 91, "lng": -74.0},
    "radio_cero": {"lat": 4.7, "lng": -74.0, "radioMetros": 0},
    "tipo_desconocido": {"tipo": "moto"},
    "bateria_min_fuera_de_rango": {"bateriaMin": 101},
    "pagina_cero": {"pagina": 0},
    "tamano_excesivo": {"tamano": 1000},
}


@pytest.mark.parametrize("params", PARAMETROS_INVALIDOS.values(), ids=PARAMETROS_INVALIDOS.keys())
async def test_parametros_invalidos_responden_400(cliente, params):
    r = await cliente.get("/vehiculos", params=params)
    assert r.status_code == 400
