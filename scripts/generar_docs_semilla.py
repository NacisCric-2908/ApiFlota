"""Genera docs/semilla.md (los 30 vehículos semilla) a partir del código, para que no se desactualice.

    make docs-semilla

La localidad se calcula con punto-en-polígono en Python puro sobre el mismo GeoJSON que usa el
servicio; un test verifica que coincide con lo que resuelve MongoDB.
"""

import json

from app.db.localidades import RUTA_GEOJSON
from app.db.semilla import CENTRO_LAT, CENTRO_LNG, COLUMNAS, FILAS, PASO, SIN_ACTUALIZAR, generar_vehiculos


def _en_anillo(lng: float, lat: float, anillo: list[list[float]]) -> bool:
    """Trazado de rayos: cuenta cuántas veces un rayo horizontal cruza el borde."""
    dentro = False
    for (x1, y1), (x2, y2) in zip(anillo, anillo[1:]):
        if (y1 > lat) != (y2 > lat) and lng < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            dentro = not dentro
    return dentro


def localidad_de(lng: float, lat: float, localidades: list[dict]) -> dict | None:
    for f in localidades:
        for poligono in f["geometry"]["coordinates"]:  # MultiPolygon
            exterior, *huecos = poligono
            if _en_anillo(lng, lat, exterior) and not any(_en_anillo(lng, lat, h) for h in huecos):
                return f["properties"]
    return None


def generar() -> str:
    localidades = json.loads(RUTA_GEOJSON.read_text(encoding="utf-8"))["features"]
    vehiculos = generar_vehiculos()

    filas = []
    for i, v in enumerate(vehiculos):
        lng, lat = v["ubicacion"]["coordinates"]
        loc = localidad_de(lng, lat, localidades)
        vieja = "sí" if i in SIN_ACTUALIZAR else "no"
        filas.append(
            f"| `{v['_id']}` | {v['tipo']} | {v['bateriaPct']} % | {v['estado']} | {lat:.6f} | {lng:.6f} "
            f"| {loc['nombre'] if loc else '(fuera)'} | {vieja} |"
        )

    return "\n".join(
        [
            "# Datos semilla de Flota",
            "",
            "> Generado con `make docs-semilla` a partir de `app/db/semilla.py`. No editar a mano.",
            "",
            f"Al arrancar con la base vacía el servicio carga **{len(vehiculos)} vehículos** en una "
            f"cuadrícula de {COLUMNAS} x {FILAS}, con {PASO * 111_320:.0f} m de separación, centrada en "
            f"**lat {CENTRO_LAT}, lng {CENTRO_LNG}** (las coordenadas de ejemplo del enunciado del clúster). "
            "Todos quedan a menos de ~350 m del centro.",
            "",
            "**Para el grupo de Viajes y zonas:** las zonas que siembren (al menos una prohibida, una de "
            "recargo y dos de parqueo) deben cubrir esta misma área. Una búsqueda de 500 m desde el centro "
            "encuentra los 30 vehículos.",
            "",
            "Se dejó variedad a propósito para poder probar las reglas del MID:",
            "",
            "- Batería menor a 25 %: no debe recomendarse. Menor a 15 %: alerta. Menor a 10 %: alerta alta.",
            "- Estados `disponible`, `en_viaje` y `mantenimiento`.",
            "- Dos vehículos con la ubicación sin actualizar hace más de 2 horas (alerta por inactividad).",
            "",
            "| id | tipo | batería | estado | lat | lng | localidad | ubicación vieja (>2 h) |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
            *filas,
            "",
        ]
    )


if __name__ == "__main__":
    print(generar(), end="")
