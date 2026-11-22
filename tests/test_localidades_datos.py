"""Calidad del dato de localidades: las 20 forman una cobertura sin huecos ni traslapes."""

import json

from app.db.localidades import RUTA_GEOJSON, buscar_por_punto
from scripts.preparar_localidades import verificar_cobertura
from shapely.geometry import shape


def _localidades():
    return json.loads(RUTA_GEOJSON.read_text(encoding="utf-8"))["features"]


def test_las_20_localidades_no_tienen_huecos_ni_traslapes():
    feats = _localidades()
    assert len(feats) == 20
    # Falla con un mensaje claro si dos localidades se traslapan o si hay un hueco entre ellas.
    verificar_cobertura([f["properties"]["nombre"] for f in feats], [shape(f["geometry"]) for f in feats])


async def test_un_punto_exactamente_sobre_un_borde_cuenta_como_dentro(cliente, localidades):
    """Un vértice del límite pertenece a la localidad (y a sus vecinas): nunca queda «fuera de Bogotá»."""
    for f in _localidades():
        lng, lat = f["geometry"]["coordinates"][0][0][0]
        encontrada = await buscar_por_punto(localidades, lng, lat)
        assert encontrada is not None, f"{f['properties']['nombre']}: el vértice {lng},{lat} quedó fuera"


async def test_los_puntos_de_referencia_siguen_en_su_localidad(cliente):
    esperado = {
        (4.5981, -74.0760): "17",  # Plaza de Bolívar
        (4.6059, -74.0560): "03",  # Monserrate
        (4.7016, -74.1469): "09",  # Aeropuerto El Dorado
        (4.6381, -74.0840): "13",  # Universidad Nacional
        (4.6948, -74.0306): "01",  # Parque de Usaquén
        (4.7110, -74.0721): "11",  # centro de la semilla
    }
    for (lat, lng), codigo in esperado.items():
        r = await cliente.get("/localidades/verificar", params={"lat": lat, "lng": lng})
        assert r.json()["localidad"]["codigo"] == codigo, (lat, lng)
