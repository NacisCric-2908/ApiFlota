"""Genera app/data/localidades_bogota.geojson a partir del dataset oficial de Datos Abiertos Bogotá.

Fuente: «Localidad. Bogotá D.C» (Unidad Administrativa Especial de Catastro Distrital, IDECA),
licencia Creative Commons Attribution 4.0.
https://datosabiertos.bogota.gov.co/dataset/localidad-bogota-d-c

El original es JSON de Esri (anillos). Aquí se convierte a GeoJSON válido para MongoDB (2dsphere):
geometrías reparadas, anillos exteriores antihorarios, simplificadas a ~5 m y con 5 decimales.

Se ejecuta con Docker (no requiere instalar nada en la máquina):
    make localidades
"""

import json
import sys
import urllib.request
from pathlib import Path

from shapely import make_valid, set_precision
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


def limpiar(geom):
    geom = make_valid(geom)
    geom = geom.simplify(TOLERANCIA_GRADOS, preserve_topology=True)
    geom = set_precision(geom, CUADRICULA_GRADOS)
    geom = make_valid(geom)
    if geom.geom_type == "GeometryCollection":  # make_valid puede dejar restos de líneas o puntos
        geom = unary_union([g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon")])
    poligonos = [geom] if isinstance(geom, Polygon) else list(geom.geoms)
    return MultiPolygon([orient(p, sign=1.0) for p in poligonos if not p.is_empty])


def main() -> None:
    crudo = descargar()
    caracteristicas = []
    for f in sorted(crudo["features"], key=lambda f: f["attributes"]["LocCodigo"]):
        attrs = f["attributes"]
        geom = limpiar(a_poligono(f["geometry"]["rings"]))
        assert geom.is_valid and not geom.is_empty, attrs["LocNombre"]
        caracteristicas.append(
            {
                "type": "Feature",
                "properties": {
                    "codigo": attrs["LocCodigo"],
                    "nombre": NOMBRES[attrs["LocCodigo"]],
                    "areaM2": round(attrs["LocArea"]),
                },
                "geometry": mapping(geom),
            }
        )
    salida = {
        "type": "FeatureCollection",
        "fuente": "Datos Abiertos Bogotá - Localidad. Bogotá D.C (Catastro Distrital / IDECA), CC BY 4.0",
        "features": caracteristicas,
    }
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(salida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(caracteristicas)} localidades -> {DESTINO} ({DESTINO.stat().st_size / 1024:.0f} KB)", file=sys.stderr)


if __name__ == "__main__":
    main()
