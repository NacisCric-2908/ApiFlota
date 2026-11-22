import pytest

# Puntos de referencia reales (lat, lng) y la localidad donde caen.
PUNTOS = {
    "plaza_de_bolivar": (4.5981, -74.0760, "17", "La Candelaria"),
    "monserrate": (4.6059, -74.0560, "03", "Santa Fe"),
    "aeropuerto_el_dorado": (4.7016, -74.1469, "09", "Fontibón"),
    "universidad_nacional": (4.6381, -74.0840, "13", "Teusaquillo"),
    "parque_de_usaquen": (4.6948, -74.0306, "01", "Usaquén"),
}
FUERA_DE_BOGOTA = {"medellin": (6.2442, -75.5812), "chia": (4.8586, -74.0586), "mar_caribe": (10.0, -75.0)}


def en(lat, lng):
    return {"ubicacion": {"type": "Point", "coordinates": [lng, lat]}}


async def test_estan_las_20_localidades(cliente):
    r = await cliente.get("/localidades")
    assert r.status_code == 200
    cuerpo = r.json()
    assert [l["codigo"] for l in cuerpo] == [f"{i:02d}" for i in range(1, 21)]
    assert {"La Candelaria", "Usaquén", "Ciudad Bolívar", "Sumapaz"} <= {l["nombre"] for l in cuerpo}
    assert all(l["vehiculos"]["total"] == 0 for l in cuerpo)


@pytest.mark.parametrize(("lat", "lng", "codigo", "nombre"), PUNTOS.values(), ids=PUNTOS.keys())
async def test_verificar_un_punto_dentro_de_bogota(cliente, lat, lng, codigo, nombre):
    r = await cliente.get("/localidades/verificar", params={"lat": lat, "lng": lng})
    assert r.status_code == 200
    assert r.json() == {"dentroDeBogota": True, "localidad": {"codigo": codigo, "nombre": nombre}}


@pytest.mark.parametrize(("lat", "lng"), FUERA_DE_BOGOTA.values(), ids=FUERA_DE_BOGOTA.keys())
async def test_verificar_un_punto_fuera_de_bogota(cliente, lat, lng):
    r = await cliente.get("/localidades/verificar", params={"lat": lat, "lng": lng})
    assert r.status_code == 200
    assert r.json() == {"dentroDeBogota": False, "localidad": None}


@pytest.mark.parametrize("params", [{"lat": 4.7}, {"lng": -74.0}, {"lat": 95, "lng": -74}, {"lat": "x", "lng": 1}])
async def test_verificar_con_parametros_invalidos_responde_400(cliente, params):
    assert (await cliente.get("/localidades/verificar", params=params)).status_code == 400


async def test_detalle_devuelve_un_feature_geojson(cliente):
    r = await cliente.get("/localidades/17")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["type"] == "Feature"
    assert cuerpo["properties"]["nombre"] == "La Candelaria"
    assert cuerpo["geometry"]["type"] == "MultiPolygon"


async def test_detalle_de_localidad_inexistente_responde_404(cliente):
    r = await cliente.get("/localidades/99")
    assert r.status_code == 404
    assert r.json()["codigo"] == "localidad_no_encontrada"


async def test_el_vehiculo_creado_trae_su_localidad(cliente, payload):
    r = await cliente.post("/vehiculos", json=payload(**en(4.5981, -74.0760)))
    assert r.status_code == 201
    assert r.json()["localidad"] == {"codigo": "17", "nombre": "La Candelaria"}
    assert "slug" not in r.json()["localidad"]


@pytest.mark.parametrize(("lat", "lng"), FUERA_DE_BOGOTA.values(), ids=FUERA_DE_BOGOTA.keys())
async def test_crear_fuera_de_bogota_responde_400(cliente, payload, lat, lng):
    r = await cliente.post("/vehiculos", json=payload(**en(lat, lng)))
    assert r.status_code == 400
    assert r.json()["codigo"] == "fuera_de_bogota"
    assert r.json()["detalle"] == {"lat": lat, "lng": lng}
    assert (await cliente.get("/vehiculos")).json()["total"] == 0


async def test_reemplazar_fuera_de_bogota_responde_400_y_no_cambia_nada(cliente, crear_vehiculo, payload):
    original = await crear_vehiculo(id="v1")
    r = await cliente.put("/vehiculos/v1", json=payload(**en(6.2442, -75.5812)))
    assert r.status_code == 400 and r.json()["codigo"] == "fuera_de_bogota"
    assert (await cliente.get("/vehiculos/v1")).json() == original


async def test_mover_el_vehiculo_actualiza_su_localidad(cliente, crear_vehiculo):
    v = await crear_vehiculo(id="v1", estado="en_viaje", **en(4.5981, -74.0760))
    assert v["localidad"]["nombre"] == "La Candelaria"
    r = await cliente.patch(
        "/vehiculos/v1/estado",
        json={"estado": "disponible", "ubicacion": {"type": "Point", "coordinates": [-74.0306, 4.6948]}},
    )
    assert r.status_code == 200
    assert r.json()["localidad"] == {"codigo": "01", "nombre": "Usaquén"}


async def test_mover_fuera_de_bogota_responde_400_y_no_cambia_el_estado(cliente, crear_vehiculo):
    await crear_vehiculo(id="v1", estado="en_viaje")
    r = await cliente.patch(
        "/vehiculos/v1/estado",
        json={"estado": "disponible", "ubicacion": {"type": "Point", "coordinates": [-75.5812, 6.2442]}},
    )
    assert r.status_code == 400 and r.json()["codigo"] == "fuera_de_bogota"
    assert (await cliente.get("/vehiculos/v1")).json()["estado"] == "en_viaje"


async def test_cambiar_estado_sin_ubicacion_conserva_la_localidad(cliente, crear_vehiculo):
    v = await crear_vehiculo(id="v1", **en(4.5981, -74.0760))
    r = await cliente.patch("/vehiculos/v1/estado", json={"estado": "en_viaje"})
    assert r.json()["localidad"] == v["localidad"]


@pytest.mark.parametrize("valor", ["17", "La Candelaria", "la-candelaria", "LA CANDELARIA"])
async def test_filtrar_por_localidad_acepta_codigo_o_nombre(cliente, crear_vehiculo, valor):
    await crear_vehiculo(id="centro", **en(4.5981, -74.0760))
    await crear_vehiculo(id="norte", **en(4.6948, -74.0306))
    r = await cliente.get("/vehiculos", params={"localidad": valor})
    assert [v["id"] for v in r.json()["items"]] == ["centro"]


async def test_filtrar_por_localidad_ignora_las_tildes(cliente, crear_vehiculo):
    await crear_vehiculo(id="norte", **en(4.6948, -74.0306))
    for valor in ("Usaquén", "usaquen", "USAQUEN"):
        r = await cliente.get("/vehiculos", params={"localidad": valor})
        assert [v["id"] for v in r.json()["items"]] == ["norte"], valor


async def test_localidad_combinada_con_cercania(cliente, crear_vehiculo):
    await crear_vehiculo(id="centro", **en(4.5981, -74.0760))
    await crear_vehiculo(id="otro", **en(4.5985, -74.0765))
    r = await cliente.get(
        "/vehiculos", params={"lat": 4.5981, "lng": -74.0760, "localidad": "17", "radioMetros": 1000}
    )
    assert [v["id"] for v in r.json()["items"]] == ["centro", "otro"]
    assert r.json()["total"] == 2


async def test_el_conteo_por_localidad_refleja_los_estados(cliente, crear_vehiculo):
    await crear_vehiculo(id="a", estado="disponible", **en(4.5981, -74.0760))
    await crear_vehiculo(id="b", estado="en_viaje", **en(4.5981, -74.0760))
    await crear_vehiculo(id="c", estado="disponible", **en(4.6948, -74.0306))
    por_codigo = {l["codigo"]: l["vehiculos"] for l in (await cliente.get("/localidades")).json()}
    assert por_codigo["17"] == {"total": 2, "disponible": 1, "en_viaje": 1, "mantenimiento": 0}
    assert por_codigo["01"]["total"] == 1
    assert por_codigo["02"]["total"] == 0


async def test_existe_el_indice_geoespacial_de_localidades(cliente, localidades):
    indices = await localidades.index_information()
    assert any(("geometria", "2dsphere") in i["key"] for i in indices.values())
