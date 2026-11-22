from math import asin, cos, radians, sin, sqrt

from app.db.semilla import CENTRO_LAT, CENTRO_LNG, cargar_semilla_si_vacia, generar_vehiculos


def distancia_m(lng1, lat1, lng2, lat2):
    d_lat, d_lng = radians(lat2 - lat1), radians(lng2 - lng1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2) ** 2
    return 2 * 6_371_000 * asin(sqrt(a))


def test_la_semilla_tiene_30_vehiculos_con_ids_unicos():
    vehiculos = generar_vehiculos()
    assert len(vehiculos) == 30
    assert len({v["_id"] for v in vehiculos}) == 30


def test_todos_quedan_a_menos_de_500_m_del_centro():
    for v in generar_vehiculos():
        lng, lat = v["ubicacion"]["coordinates"]
        assert distancia_m(CENTRO_LNG, CENTRO_LAT, lng, lat) < 500


def test_la_semilla_sirve_para_la_demostracion():
    vehiculos = generar_vehiculos()
    recomendables = [v for v in vehiculos if v["estado"] == "disponible" and v["bateriaPct"] >= 25]
    assert len(recomendables) >= 3
    assert any(v["bateriaPct"] < 25 and v["estado"] == "disponible" for v in vehiculos)  # no recomendable
    assert any(v["bateriaPct"] < 10 for v in vehiculos)  # alerta alta
    assert {v["tipo"] for v in vehiculos} == {"scooter", "bicicleta"}
    assert {v["estado"] for v in vehiculos} == {"disponible", "en_viaje", "mantenimiento"}


async def test_se_carga_solo_si_la_coleccion_esta_vacia(cliente, coleccion):
    assert await cargar_semilla_si_vacia(coleccion) == 30
    assert await coleccion.count_documents({}) == 30
    assert await cargar_semilla_si_vacia(coleccion) == 0
    assert await coleccion.count_documents({}) == 30


async def test_existe_el_indice_geoespacial(cliente, coleccion):
    indices = await coleccion.index_information()
    assert any(("ubicacion", "2dsphere") in i["key"] for i in indices.values())
