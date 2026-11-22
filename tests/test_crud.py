import pytest


async def test_crear_devuelve_201_con_location_y_valores(cliente, payload):
    r = await cliente.post("/vehiculos", json=payload(id="veh-9001"))
    assert r.status_code == 201
    assert r.headers["location"] == "/vehiculos/veh-9001"
    cuerpo = r.json()
    assert cuerpo["id"] == "veh-9001"
    assert cuerpo["estado"] == "disponible"
    assert "actualizadoEn" in cuerpo
    assert "distanciaMetros" not in cuerpo


async def test_crear_sin_id_genera_uno(cliente, payload):
    r = await cliente.post("/vehiculos", json=payload())
    assert r.status_code == 201
    assert r.json()["id"].startswith("veh-")


async def test_crear_con_id_repetido_responde_409(cliente, payload):
    await cliente.post("/vehiculos", json=payload(id="veh-9001"))
    r = await cliente.post("/vehiculos", json=payload(id="veh-9001"))
    assert r.status_code == 409
    assert r.json()["codigo"] == "vehiculo_duplicado"


DATOS_INVALIDOS = {
    "bateria_mayor_a_100": {"bateriaPct": 101},
    "bateria_negativa": {"bateriaPct": -1},
    "bateria_decimal": {"bateriaPct": 50.5},
    "tipo_desconocido": {"tipo": "moto"},
    "estado_desconocido": {"estado": "roto"},
    "latitud_fuera_de_rango": {"ubicacion": {"type": "Point", "coordinates": [-74.0, 95.0]}},
    "longitud_fuera_de_rango": {"ubicacion": {"type": "Point", "coordinates": [-200.0, 4.7]}},
    "una_sola_coordenada": {"ubicacion": {"type": "Point", "coordinates": [-74.0]}},
    "geometria_no_punto": {"ubicacion": {"type": "Polygon", "coordinates": [-74.0, 4.7]}},
    "id_con_caracteres_invalidos": {"id": "veh 1/../"},
}


@pytest.mark.parametrize("cambios", DATOS_INVALIDOS.values(), ids=DATOS_INVALIDOS.keys())
async def test_crear_con_datos_invalidos_responde_400(cliente, payload, cambios):
    r = await cliente.post("/vehiculos", json=payload(**cambios))
    assert r.status_code == 400
    cuerpo = r.json()
    assert cuerpo["codigo"] == "solicitud_invalida"
    assert cuerpo["detalle"]["errores"]


async def test_crear_sin_cuerpo_responde_400(cliente):
    r = await cliente.post("/vehiculos")
    assert r.status_code == 400


async def test_detalle_y_404(cliente, crear_vehiculo):
    creado = await crear_vehiculo(id="veh-9002")
    r = await cliente.get("/vehiculos/veh-9002")
    assert r.status_code == 200
    assert r.json() == creado

    r = await cliente.get("/vehiculos/no-existe")
    assert r.status_code == 404
    assert r.json()["codigo"] == "vehiculo_no_encontrado"


async def test_reemplazar_cambia_los_campos_y_actualiza_la_fecha(cliente, crear_vehiculo, payload):
    original = await crear_vehiculo(id="veh-9003")
    nuevo = payload(tipo="bicicleta", bateriaPct=10, estado="mantenimiento")
    r = await cliente.put("/vehiculos/veh-9003", json=nuevo)
    assert r.status_code == 200
    cuerpo = r.json()
    assert (cuerpo["tipo"], cuerpo["bateriaPct"], cuerpo["estado"]) == ("bicicleta", 10, "mantenimiento")
    assert cuerpo["actualizadoEn"] >= original["actualizadoEn"]
    assert (await cliente.get("/vehiculos/veh-9003")).json() == cuerpo


async def test_reemplazar_inexistente_responde_404(cliente, payload):
    r = await cliente.put("/vehiculos/no-existe", json=payload())
    assert r.status_code == 404


async def test_reemplazar_con_datos_invalidos_responde_400(cliente, crear_vehiculo, payload):
    await crear_vehiculo(id="veh-9004")
    r = await cliente.put("/vehiculos/veh-9004", json=payload(bateriaPct=500))
    assert r.status_code == 400


async def test_eliminar_responde_204_y_luego_404(cliente, crear_vehiculo):
    await crear_vehiculo(id="veh-9005")
    assert (await cliente.delete("/vehiculos/veh-9005")).status_code == 204
    assert (await cliente.get("/vehiculos/veh-9005")).status_code == 404
    assert (await cliente.delete("/vehiculos/veh-9005")).status_code == 404


async def test_no_se_puede_eliminar_un_vehiculo_en_viaje(cliente, crear_vehiculo):
    await crear_vehiculo(id="veh-9006", estado="en_viaje")
    r = await cliente.delete("/vehiculos/veh-9006")
    assert r.status_code == 409
    assert r.json()["codigo"] == "vehiculo_en_viaje"
    assert (await cliente.get("/vehiculos/veh-9006")).status_code == 200
