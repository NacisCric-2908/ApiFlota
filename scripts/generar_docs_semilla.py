"""Genera la documentación derivada de la semilla, para que no se desactualice:

    docs/semilla.md                        los 30 vehículos, las zonas propuestas y los resultados esperados
    docs/geo/zonas_semilla_postgis.sql     las mismas zonas como SQL para PostGIS

    make docs-semilla

La localidad y las zonas se calculan con punto-en-polígono en Python puro sobre el mismo GeoJSON que usa el
servicio; un test verifica que coincide con lo que resuelve MongoDB.
"""

import json
import math
import sys

from app.db.localidades import RUTA_GEOJSON
from app.db.semilla import CENTRO_LAT, CENTRO_LNG, COLUMNAS, FILAS, PASO, SIN_ACTUALIZAR, generar_vehiculos

# --- Zonas que Flota propone a Viajes y zonas (1 prohibida, 1 de recargo, 2 de parqueo) -----------------
# Cajas (lng_min, lat_min, lng_max, lat_max) que cubren toda la cuadrícula de la semilla con un margen de
# ~50 m. La prohibida encierra a veh-0016 (disponible, 59 % de batería, el más cercano al centro) para que se
# vea la regla «descartar vehículos en zona prohibida». La franja central norte queda sin zona a propósito.
ZONAS = [
    {"nombre": "Prohibida Centro", "tipo": "prohibida", "caja": (-74.0719, 4.7107, -74.0714, 4.7113)},
    {"nombre": "Recargo Oriente", "tipo": "recargo", "caja": (-74.0710, 4.7086, -74.0694, 4.7134)},
    {"nombre": "Parqueo Occidente", "tipo": "parqueo", "caja": (-74.0748, 4.7086, -74.0730, 4.7134)},
    {"nombre": "Parqueo Sur", "tipo": "parqueo", "caja": (-74.0730, 4.7086, -74.0710, 4.7100)},
]
PUNTOS_DE_PRUEBA = [
    ("Dentro de la zona prohibida", 4.7110, -74.07165),
    ("En la zona de recargo (paso 7 de la demostración: finalizar el viaje)", 4.7110, -74.0702),
    ("En una zona de parqueo", 4.7092, -74.0720),
    ("Fuera de todas las zonas", 4.7125, -74.0721),
]
RADIO_TIERRA_M = 6_378_137  # el que usa MongoDB en las consultas esféricas


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


def anillo(caja: tuple) -> list[list[float]]:
    """Anillo cerrado y antihorario (lo que esperan GeoJSON y PostGIS)."""
    x0, y0, x1, y1 = caja
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]


def geometria(zona: dict) -> dict:
    return {"type": "Polygon", "coordinates": [anillo(zona["caja"])]}


def zonas_de(lng: float, lat: float) -> list[dict]:
    return [z for z in ZONAS if _en_anillo(lng, lat, anillo(z["caja"]))]


def distancia_m(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    f1, f2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((f2 - f1) / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2
    return 2 * RADIO_TIERRA_M * math.asin(math.sqrt(a))


def recomendaciones(vehiculos: list[dict]) -> tuple[list[dict], list[str]]:
    """Reglas del MID de Flota desde el centro de la semilla: devuelve (3 mejores, descartados por zona)."""
    candidatos, por_zona = [], []
    for v in vehiculos:
        lng, lat = v["ubicacion"]["coordinates"]
        d = distancia_m(CENTRO_LNG, CENTRO_LAT, lng, lat)
        if v["estado"] != "disponible" or d > 500 or v["bateriaPct"] < 25:
            continue
        if any(z["tipo"] == "prohibida" for z in zonas_de(lng, lat)):
            por_zona.append(v["_id"])
            continue
        candidatos.append({"id": v["_id"], "distancia": d, "bateria": v["bateriaPct"], "puntaje": d - v["bateriaPct"] * 2})
    return sorted(candidatos, key=lambda c: c["puntaje"])[:3], por_zona


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

    # --- zonas propuestas ---
    filas_zonas = []
    for z in ZONAS:
        dentro = [v["_id"] for v in vehiculos if z in zonas_de(*v["ubicacion"]["coordinates"])]
        x0, y0, x1, y1 = z["caja"]
        filas_zonas.append(
            f"| {z['nombre']} | {z['tipo']} | lat {y0} a {y1}<br>lng {x0} a {x1} | {len(dentro)} | "
            + ", ".join(f"`{d}`" for d in dentro)
            + " |"
        )
    filas_puntos = []
    for nombre, lat, lng in PUNTOS_DE_PRUEBA:
        zs = zonas_de(lng, lat)
        permitida = not any(z["tipo"] == "prohibida" for z in zs)
        filas_puntos.append(
            f"| {nombre} | {lat} | {lng} | `{'true' if permitida else 'false'}` | "
            + (", ".join(z["nombre"] for z in zs) or "(ninguna)")
            + " |"
        )
    top3, descartados = recomendaciones(vehiculos)
    filas_top = [
        f"| {i}. | `{c['id']}` | {c['distancia']:.0f} m | {c['bateria']} % | {c['puntaje']:.0f} |"
        for i, c in enumerate(top3, 1)
    ]
    geojson = json.dumps(
        {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {"nombre": z["nombre"], "tipo": z["tipo"]}, "geometry": geometria(z)}
                for z in ZONAS
            ],
        },
        ensure_ascii=False,
        indent=2,
    )

    return "\n".join(
        [
            "# Datos semilla de Flota",
            "",
            "> Generado con `make docs-semilla` a partir de `app/db/semilla.py`. No editar a mano.",
            "",
            f"Al arrancar con la base vacía el servicio carga **{len(vehiculos)} vehículos** en una "
            f"cuadrícula de {COLUMNAS} x {FILAS}, con {PASO * 111_320:.0f} m de separación, centrada en "
            f"**lat {CENTRO_LAT}, lng {CENTRO_LNG}** (las coordenadas de ejemplo del enunciado del clúster; "
            "cae en la localidad de Suba). Todos quedan a menos de ~350 m del centro, así que una búsqueda de "
            "500 m desde ese punto los encuentra a todos.",
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
            "## Zonas propuestas para Viajes y zonas",
            "",
            "El enunciado pide sembrar al menos 4 zonas (1 prohibida, 1 de recargo y 2 de parqueo) que cubran el "
            "área de los vehículos y acordarlas con Flota desde el primer día. **Esta es la propuesta de Flota, lista "
            "para usar:** si Viajes y zonas la adopta tal cual, las demostraciones funcionan con los datos de ambos "
            "grupos. Si prefieren otras coordenadas, avisen: solo hay que mantener estas propiedades.",
            "",
            "| Zona | Tipo | Cubre | Vehículos semilla | Cuáles |",
            "| --- | --- | --- | --- | --- |",
            *filas_zonas,
            "",
            "Propiedades que se deben conservar si se cambian:",
            "",
            "- Las zonas cubren la cuadrícula de la semilla y están dentro de Bogotá (todas, en Suba).",
            "- Las zonas no se traslapan (comparten bordes, no área).",
            f"- La zona prohibida contiene al menos un vehículo recomendable ({', '.join(f'`{d}`' for d in descartados)}), "
            "para que se vea la regla de descartar por zona, **pero no a todos**: la demostración siempre debe "
            "producir al menos una recomendación.",
            "- Queda una franja sin ninguna zona, para probar `permitida: true` fuera de las zonas.",
            "- La zona de recargo es donde se finaliza el viaje en el paso 7 de la demostración.",
            "",
            "### Puntos de prueba para `GET /zonas/verificar?lat&lng`",
            "",
            "| Caso | lat | lng | `permitida` | Zonas devueltas |",
            "| --- | --- | --- | --- | --- |",
            *filas_puntos,
            "",
            "### Resultado esperado de la recomendación desde el centro",
            "",
            f"`GET /recomendaciones/vehiculo?lat={CENTRO_LAT}&lng={CENTRO_LNG}` aplicando las reglas del enunciado "
            f"(500 m, batería de al menos 25 %, sin zona prohibida, `puntaje = distancia − batería × 2`). "
            f"Con estas zonas se descarta {', '.join(f'`{d}`' for d in descartados)} por estar en la zona prohibida. "
            "Los 3 mejores (distancias aproximadas, calculadas sobre la esfera como lo hace MongoDB):",
            "",
            "| Puesto | Vehículo | Distancia | Batería | Puntaje |",
            "| --- | --- | --- | --- | --- |",
            *filas_top,
            "",
            "### Las zonas como GeoJSON",
            "",
            "```json",
            geojson,
            "```",
            "",
            "Para cargarlas en PostGIS: [`geo/zonas_semilla_postgis.sql`](geo/zonas_semilla_postgis.sql). "
            "Guía completa de uso de los datos geoespaciales: [geoespacial.md](geoespacial.md).",
            "",
        ]
    )


def generar_sql() -> str:
    valores = ",\n".join(
        f"    ('{z['nombre']}', '{z['tipo']}',\n"
        f"     ST_SetSRID(ST_GeomFromGeoJSON('{json.dumps(geometria(z))}'), 4326))"
        for z in ZONAS
    )
    return f"""-- Zonas semilla que Flota propone a Viajes y zonas (1 prohibida, 1 de recargo, 2 de parqueo).
-- GENERADO con `make docs-semilla` a partir de scripts/generar_docs_semilla.py. No editar a mano.
--
-- Requiere haber ejecutado antes cargar_localidades_postgis.sql (usa la tabla bogota para validar).
-- Uso:  psql "$DATABASE_URL" -f zonas_semilla_postgis.sql

CREATE EXTENSION IF NOT EXISTS postgis;

DROP TABLE IF EXISTS zonas;
CREATE TABLE zonas (
    id       serial PRIMARY KEY,
    nombre   text NOT NULL UNIQUE,
    tipo     text NOT NULL CHECK (tipo IN ('prohibida', 'recargo', 'parqueo')),
    poligono geometry(Polygon, 4326) NOT NULL CHECK (ST_IsValid(poligono))
);
CREATE INDEX zonas_poligono_gix ON zonas USING GIST (poligono);

INSERT INTO zonas (nombre, tipo, poligono) VALUES
{valores};

-- Comprobación: todas las zonas deben quedar dentro de Bogotá (debe devolver 0 filas).
SELECT z.nombre AS zona_fuera_de_bogota
FROM zonas z, bogota b
WHERE NOT ST_CoveredBy(z.poligono, b.geom);
"""


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "md"
    print(generar_sql() if modo == "sql" else generar(), end="")
