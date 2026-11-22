"""Genera app/data/localidades_bogota.geojson a partir del dataset oficial de Datos Abiertos Bogotá.

Fuente: «Localidad. Bogotá D.C» (Unidad Administrativa Especial de Catastro Distrital, IDECA),
licencia Creative Commons Attribution 4.0.
https://datosabiertos.bogota.gov.co/dataset/localidad-bogota-d-c

El original es JSON de Esri (anillos) en MAGNA-SIRGAS geográfico. Aquí se convierte a GeoJSON válido
para MongoDB y PostGIS (2dsphere / SRID 4326): anillos exteriores antihorarios, simplificado a ~5 m y
con 5 decimales (~1 m).

Las 20 localidades forman una **cobertura** (se tocan por sus bordes, sin huecos ni traslapes). Por eso se
simplifican TODAS JUNTAS con `coverage_simplify`, que conserva los bordes compartidos. Simplificar cada una
por separado deja huecos y traslapes de hasta ~5.000 m² entre vecinas, y un punto dentro de un hueco se
rechazaría como «fuera de Bogotá». El script falla si la cobertura no queda limpia.

Se ejecuta con Docker (no requiere instalar nada en la máquina):
    make localidades
"""

import itertools
import json
import math
import sys
import urllib.request
from pathlib import Path

from shapely import coverage_simplify, set_precision
from shapely.geometry import MultiPolygon, Polygon, mapping
from shapely.geometry.polygon import LinearRing, orient
from shapely.ops import unary_union

URL = (
    "https://datosabiertos.bogota.gov.co/dataset/856cb657-8ca3-4ee8-857f-37211173b1f8/"
    "resource/497b8756-0927-4aee-8da9-ca4e32ca3a8a/download/loca.json"
)
DESTINO = Path(__file__).resolve().parent.parent / "app" / "data" / "localidades_bogota.geojson"
# El dataset trae los nombres en mayúsculas y sin tildes; estos son los nombres oficiales.
NOMBRES = {
    "01": "Usaquén", "02": "Chapinero", "03": "Santa Fe", "04": "San Cristóbal", "05": "Usme",
    "06": "Tunjuelito", "07": "Bosa", "08": "Kennedy", "09": "Fontibón", "10": "Engativá",
    "11": "Suba", "12": "Barrios Unidos", "13": "Teusaquillo", "14": "Los Mártires",
    "15": "Antonio Nariño", "16": "Puente Aranda", "17": "La Candelaria",
    "18": "Rafael Uribe Uribe", "19": "Ciudad Bolívar", "20": "Sumapaz",
}  # fmt: skip
TOLERANCIA_GRADOS = 0.00005  # ~5 m
CUADRICULA_GRADOS = 0.00001  # 5 decimales (~1 m)
M2_POR_GRADO2 = (111_320**2) * math.cos(math.radians(4.65))  # aproximado, solo para el chequeo
TOLERANCIA_M2 = 1.0  # máximo traslape o hueco aceptado


def descargar() -> dict:
    peticion = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(peticion, timeout=120) as r:
        return json.load(r)


def a_poligono(anillos: list[list[list[float]]]):
    """En Esri los anillos exteriores van en sentido horario y los huecos en antihorario."""
    exteriores, huecos = [], []
    for coords in anillos:
        anillo = LinearRing(coords)
        (exteriores if anillo.is_ccw is False else huecos).append(Polygon(anillo))
    geom = unary_union(exteriores)
    if huecos:
        geom = geom.difference(unary_union(huecos))
    return geom


def verificar_cobertura(nombres: list[str], geoms: list) -> None:
    """Falla si hay polígonos inválidos, traslapes o huecos entre localidades vecinas."""
    invalidas = [n for n, g in zip(nombres, geoms) if not g.is_valid or g.is_empty]
    assert not invalidas, f"geometrías inválidas: {invalidas}"
    for (a, ga), (b, gb) in itertools.combinations(zip(nombres, geoms), 2):
        if ga.intersects(gb):
            traslape = ga.intersection(gb).area * M2_POR_GRADO2
            assert traslape <= TOLERANCIA_M2, f"{a} y {b} se traslapan {traslape:.0f} m²"
    union = unary_union(geoms)
    huecos = sum(Polygon(r).area for p in getattr(union, "geoms", [union]) for r in p.interiors) * M2_POR_GRADO2
    assert huecos <= TOLERANCIA_M2, f"hay huecos entre localidades que suman {huecos:.0f} m²"


def main() -> None:
    crudo = descargar()
    caracteristicas = sorted(crudo["features"], key=lambda f: f["attributes"]["LocCodigo"])
    nombres = [NOMBRES[f["attributes"]["LocCodigo"]] for f in caracteristicas]
    originales = [a_poligono(f["geometry"]["rings"]) for f in caracteristicas]
    verificar_cobertura(nombres, originales)  # el dato oficial debe ser una cobertura limpia

    # Simplificar juntas (conserva los bordes compartidos) y redondear punto a punto: el mismo vértice
    # compartido se redondea igual en las dos vecinas, así no se abren huecos.
    simplificadas = [
        set_precision(g, CUADRICULA_GRADOS, mode="pointwise")
        for g in coverage_simplify(originales, TOLERANCIA_GRADOS)
    ]
    verificar_cobertura(nombres, simplificadas)

    salida_features = []
    for f, geom in zip(caracteristicas, simplificadas):
        a = f["attributes"]
        poligonos = [geom] if isinstance(geom, Polygon) else list(geom.geoms)
        geom = MultiPolygon([orient(p, sign=1.0) for p in poligonos])
        salida_features.append(
            {
                "type": "Feature",
                "properties": {
                    "codigo": a["LocCodigo"],
                    "nombre": NOMBRES[a["LocCodigo"]],
                    "areaM2": round(a["LocArea"]),
                },
                "geometry": mapping(geom),
            }
        )
    salida = {
        "type": "FeatureCollection",
        "fuente": "Datos Abiertos Bogotá - Localidad. Bogotá D.C (Catastro Distrital / IDECA), CC BY 4.0",
        "features": salida_features,
    }
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(salida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(
        f"{len(salida_features)} localidades, cobertura sin huecos ni traslapes -> {DESTINO} "
        f"({DESTINO.stat().st_size / 1024:.0f} KB)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
