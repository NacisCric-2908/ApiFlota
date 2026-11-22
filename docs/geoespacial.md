# Guía geoespacial: Bogotá, localidades y zonas

Para los grupos que necesitan **saber si un punto está en Bogotá, en qué localidad, o manejar zonas** (sobre todo Viajes y zonas). No hace falta saber de GIS: aquí está de dónde sale el dato, cómo conseguirlo, cómo cargarlo y las consultas listas para copiar. Todo lo que hay en esta guía se ejecutó y verificó (PostGIS 3.4, MongoDB 7, Python 3.12); lo que no se pudo probar está marcado.

## 1. ¿Qué necesito? (empiece por aquí)

| Si quiere… | Haga esto | Necesita los datos |
| --- | --- | --- |
| Saber en qué localidad está un punto, o si está dentro de Bogotá | Llamar a Flota: `GET /localidades/verificar?lat&lng` (sección 3) | **No** |
| Dibujar localidades en un mapa o diseñar zonas encima | Llamar a Flota: `GET /localidades/{codigo}` devuelve el polígono (sección 3) | **No** |
| Validar en su base de datos que una zona nueva queda dentro de Bogotá, o consultar localidades junto a sus tablas | Cargar las localidades en PostGIS (sección 4) | Sí |
| Hacer «punto dentro de polígono» en su código, sin base de datos | Python con shapely (sección 6) | Sí |

**La regla de oro:** si solo necesita una respuesta puntual, llame a la API de Flota y no cargue nada. Cargue los datos solo si necesita cruzarlos con sus propias tablas.

## 2. Qué son los datos y de dónde salen

Bogotá D.C. se divide en **20 localidades** (Usaquén, Chapinero, … Sumapaz). Son polígonos oficiales que publica el Distrito como datos abiertos:

| | |
| --- | --- |
| **Conjunto** | «Localidad. Bogotá D.C.» |
| **Publicador** | Catastro Distrital / IDECA, a través de Datos Abiertos Bogotá |
| **Página** | <https://datosabiertos.bogota.gov.co/dataset/localidad-bogota-d-c> |
| **Licencia** | Creative Commons Attribution 4.0: se puede usar libremente **citando la fuente** |
| **Sistema de coordenadas** | MAGNA-SIRGAS geográfico (EPSG:4686). Para este uso equivale a WGS84 (EPSG:4326): la diferencia es de centímetros |

Formatos que ofrece el portal (los enlaces directos se verificaron):

| Formato | Enlace de descarga | ¿Sirve directo? |
| --- | --- | --- |
| Shapefile (ZIP) | `https://datosabiertos.bogota.gov.co/dataset/856cb657-8ca3-4ee8-857f-37211173b1f8/resource/30916322-7509-4cb4-8241-6be2b5109248/download/loca.zip` | Sí, con `ogr2ogr` (sección 4, vía B) |
| GeoPackage | `https://datosabiertos.bogota.gov.co/dataset/856cb657-8ca3-4ee8-857f-37211173b1f8/resource/b6c3fbda-1281-4735-8063-260e75ad95f8/download/loca.gpkg` | Sí, con `ogr2ogr` |
| «GEOJSON» | `…/resource/497b8756-0927-4aee-8da9-ca4e32ca3a8a/download/loca.json` | **No: trampa.** El portal lo etiqueta GeoJSON, pero es **JSON de Esri** (campo `rings`, sin `type`). MongoDB y PostGIS lo rechazan |

### El dato ya preparado (lo más cómodo)

Flota ya hizo la conversión y la dejó lista: **`app/data/localidades_bogota.geojson`** en este repositorio (248 KB). Es GeoJSON válido (RFC 7946), en WGS84 (`[longitud, latitud]`), con los nombres oficiales con tilde, y sirve tal cual en MongoDB, PostGIS, Leaflet, etc. Lo que se hizo con el original:

- Convertir el JSON de Esri a GeoJSON y poner los 20 nombres oficiales (el original los trae en mayúsculas y sin tildes).
- Simplificar los bordes a ~5 m y redondear a 5 decimales (~1 m), para que pese 248 KB y no 2,4 MB.
- Simplificar **las 20 juntas** para que no queden huecos ni traslapes entre vecinas. (Simplificar cada una por separado deja huecos de hasta ~5.000 m²; un test del repositorio vigila que no vuelva a pasar.)

Diferencia con el dato oficial (medida en PostGIS): como máximo el 0,16 % del área de una localidad (unos 5 m de borde, y es en las más pequeñas); en metros cuadrados la mayor es Sumapaz con ~45.000 m², el 0,006 % de sus 781 km². Si necesita el dato oficial sin tocar, use la vía B.

## 3. Opción 1 (sin cargar nada): preguntarle a la API de Flota

```bash
# ¿En qué localidad está la Plaza de Bolívar?
curl "$GATEWAY/flota/localidades/verificar?lat=4.5981&lng=-74.0760" -H "Authorization: Bearer $TOKEN"
# → {"dentroDeBogota": true, "localidad": {"codigo": "17", "nombre": "La Candelaria"}}

# Un punto fuera de Bogotá (Medellín): siempre 200, no es un error
curl "$GATEWAY/flota/localidades/verificar?lat=6.2442&lng=-75.5812" -H "Authorization: Bearer $TOKEN"
# → {"dentroDeBogota": false, "localidad": null}

# El polígono de una localidad (Feature GeoJSON, MultiPolygon)
curl "$GATEWAY/flota/localidades/17" -H "Authorization: Bearer $TOKEN"
```

Alcance necesario: `vehiculos:leer`. Detalle de cada endpoint en [integracion.md](integracion.md#6-referencia-de-endpoints).

## 4. Opción 2: cargar las localidades en PostGIS

Para Viajes y zonas, que ya usa PostgreSQL + PostGIS. Los dos caminos terminan con las localidades en una tabla consultable; elija uno.

### Vía A: desde el GeoJSON de este repositorio (solo `psql`, nada que instalar)

```bash
cd app/data        # la carpeta donde está localidades_bogota.geojson
psql "$DATABASE_URL" -f ../../docs/geo/cargar_localidades_postgis.sql
```

[`docs/geo/cargar_localidades_postgis.sql`](geo/cargar_localidades_postgis.sql) crea la extensión PostGIS si falta, la tabla `localidades` (`codigo`, `nombre`, `area_m2`, `geom` con índice GiST) y la tabla `bogota` (la unión de las 20, el contorno de la ciudad). Es idempotente: se puede ejecutar varias veces. Resultado verificado: `20 | t` (20 localidades, todas válidas); la unión es **una sola pieza, sin huecos**.

### Vía B: desde el dato oficial, sin tener nuestro repositorio

Descargar el Shapefile oficial y cargarlo con `ogr2ogr` (GDAL), que en Docker no requiere instalar nada:

```bash
curl -L -o loca.zip "https://datosabiertos.bogota.gov.co/dataset/856cb657-8ca3-4ee8-857f-37211173b1f8/resource/30916322-7509-4cb4-8241-6be2b5109248/download/loca.zip"
mkdir loca && unzip loca.zip -d loca

docker run --rm --network host -v "$PWD/loca:/data:ro" ghcr.io/osgeo/gdal:alpine-small-latest \
  ogr2ogr -f PostgreSQL "PG:host=localhost user=USUARIO password=CLAVE dbname=BASE" /data/Loca.shp \
  -nln loca_oficial -nlt MULTIPOLYGON -t_srs EPSG:4326 \
  -lco GEOMETRY_NAME=geom -lco FID=id -lco PRECISION=NO -overwrite
```

Cada opción importa (se verificó que sin ella falla o queda mal):

| Opción | Para qué |
| --- | --- |
| `-t_srs EPSG:4326` | Convierte de MAGNA-SIRGAS (4686) a WGS84, que es lo que usan MongoDB, GeoJSON y los GPS |
| `-nlt MULTIPOLYGON` | Todas las localidades son MultiPolygon; así la columna queda tipada |
| `-lco PRECISION=NO` | **Imprescindible.** Sin ella, `ogr2ogr` crea `locarea` como `numeric(18,11)` y la carga **falla** con el área de Sumapaz (`must round to an absolute value less than 10^7`) |

Queda la tabla `loca_oficial` con las columnas `loccodigo`, `locnombre` (**en mayúsculas y sin tildes**: «CANDELARIA», no «La Candelaria»), `locarea`, `geom`. Resultado verificado: 20 filas, SRID 4326, todas válidas.

> Si usa `docker run --network host` en macOS o Windows, cambie `host=localhost` por `host=host.docker.internal`.

## 5. Consultas listas para copiar (PostGIS)

Todas se ejecutaron sobre las tablas de la vía A. **El orden es `ST_MakePoint(longitud, latitud)`**: es el error más común (sección 8).

```sql
-- ¿En qué localidad está un punto?  (0 filas = fuera de Bogotá)
SELECT codigo, nombre
FROM localidades
WHERE ST_Intersects(geom, ST_SetSRID(ST_MakePoint(-74.0721, 4.7110), 4326));
--  → 11 | Suba

-- ¿Está dentro de Bogotá?
SELECT EXISTS (SELECT 1 FROM bogota
               WHERE ST_Intersects(geom, ST_SetSRID(ST_MakePoint(-74.0721, 4.7110), 4326))) AS dentro;

-- GET /zonas/verificar: en qué zonas cae un punto (permitida = ninguna es prohibida)
SELECT id, nombre, tipo
FROM zonas
WHERE ST_Intersects(poligono, ST_SetSRID(ST_MakePoint(-74.0702, 4.7110), 4326));

-- Distancia en METROS entre dos puntos (el cast a geography da metros; sin él da grados)
SELECT ST_Distance(ST_SetSRID(ST_MakePoint(-74.0721, 4.7110), 4326)::geography,
                   ST_SetSRID(ST_MakePoint(-74.07345, 4.7110), 4326)::geography);   -- 150 m

-- Todo lo que está a menos de 150 m de un punto (el radio va en metros con geography)
SELECT id FROM mi_tabla
WHERE ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(-74.0721, 4.7110), 4326)::geography, 150);

-- Devolver una zona como GeoJSON (para la respuesta de la API)
SELECT ST_AsGeoJSON(poligono) FROM zonas WHERE nombre = 'Prohibida Centro';
```

### Validar una zona nueva (V-HU1: «menos de 4 puntos o que no cierra responde 400»)

Dos capas, porque PostGIS **lanza un error** (no devuelve «inválido») con un anillo sin cerrar o con menos de 4 puntos. Valide primero en su código y deje a la base los casos que solo ella ve bien:

```python
def validar_anillo(coords: list[list[float]]) -> str | None:
    """Devuelve el motivo del rechazo (para responder 400) o None si el anillo es aceptable."""
    if len(coords) < 4:
        return "un polígono necesita al menos 4 puntos"
    if coords[0] != coords[-1]:
        return "el polígono no cierra: el último punto debe ser igual al primero"
    for lng, lat in coords:
        if not (-180 <= lng <= 180 and -90 <= lat <= 90):
            return f"coordenada fuera de rango: [{lng}, {lat}]"
        # Caja de Colombia. Atrapa la inversión típica: [4.71, -74.07] es una latitud válida (la Antártida).
        if not (-79.5 <= lng <= -66.5 and -4.5 <= lat <= 13.5):
            return f"[{lng}, {lat}] no está en Colombia: ¿invirtió el orden? Debe ser [longitud, latitud]"
    return None
```

```sql
-- Con el anillo ya filtrado: ¿es válido (sin cruzarse) y está dentro de Bogotá?
WITH g AS (SELECT ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326) AS p)
SELECT ST_IsValid(p)                     AS valido,
       ST_IsValidReason(p)               AS motivo,
       (SELECT ST_CoveredBy(p, b.geom) FROM bogota b) AS dentro_de_bogota
FROM g;
```

Comportamiento verificado con cada caso:

| Entrada | Resultado de PostGIS |
| --- | --- |
| 3 puntos, o 4 sin cerrar | **Error** `Points of LinearRing do not form a closed linestring` → valídelo antes en el código |
| Cerrado pero con un cruce («corbata») | `valido = false`, motivo `Self-intersection[-74.065 4.715]` |
| Válido y en Suba | `true`, `Valid Geometry`, `dentro_de_bogota = true` |
| Válido pero en Medellín | `true`, `Valid Geometry`, `dentro_de_bogota = false` |

## 6. Python sin base de datos (shapely)

```python
import json
from shapely.geometry import Point, shape

with open("localidades_bogota.geojson", encoding="utf-8") as f:
    localidades = [(feat["properties"], shape(feat["geometry"])) for feat in json.load(f)["features"]]


def localidad_de(lat: float, lng: float) -> dict | None:
    punto = Point(lng, lat)  # ¡longitud primero!
    for props, geom in localidades:
        if geom.intersects(punto):  # intersects: un punto exactamente en el borde cuenta como dentro
            return props
    return None


print(localidad_de(4.5981, -74.0760))  # {'codigo': '17', 'nombre': 'La Candelaria', 'areaM2': 2060243}
print(localidad_de(6.2442, -75.5812))  # None: fuera de Bogotá
```

Instalación con uv: `uv add "shapely>=2.1"`. Las 20 geometrías caben en memoria sin problema (248 KB de archivo).

## 7. Zonas semilla propuestas para Viajes y zonas

El enunciado pide sembrar 4 zonas (1 prohibida, 1 de recargo, 2 de parqueo) que cubran el área de los vehículos de Flota. **Flota ya dejó una propuesta lista**, con coordenadas, vehículos que cae en cada zona, puntos de prueba con su resultado esperado y el SQL para PostGIS:

- Coordenadas, puntos de prueba y resultado esperado de la recomendación: [semilla.md](semilla.md#zonas-propuestas-para-viajes-y-zonas)
- Carga en PostGIS: [`geo/zonas_semilla_postgis.sql`](geo/zonas_semilla_postgis.sql). Ejecútelo después de la vía A (usa la tabla `bogota`)

Verificado en PostGIS: las 4 zonas quedan dentro de Bogotá, no se traslapan, cubren 23 de los 30 vehículos (los otros 7 quedan en una franja libre a propósito) y cada punto de prueba devuelve lo documentado.

## 8. Errores comunes

| Síntoma | Causa | Solución |
| --- | --- | --- |
| Flota responde `400 fuera_de_bogota` para un punto que **sí** está en Bogotá, con `detalle: {"lat": -74.07, "lng": 4.71}` | **Latitud y longitud invertidas.** GeoJSON, PostGIS (`ST_MakePoint`) y MongoDB usan `[longitud, latitud]`; los parámetros de las APIs usan `lat` y `lng` por separado. Ojo: -74 es una latitud válida (la Antártida), por eso no sale «fuera de rango» sino «fuera de Bogotá» | Bogotá está en lat ≈ 4,6 y lng ≈ -74,07. Si en `detalle` ve `lat` ≈ -74, están al revés |
| Distancias de 0,0013 en vez de 150 | Se calculó en **grados** (tipo `geometry`) | Haga `::geography` para obtener metros |
| `ST_DWithin(..., 150)` no encuentra nada | Mismo motivo: el 150 se interpretó en grados | `::geography` en ambos argumentos |
| Error `Points of LinearRing do not form a closed linestring` | Polígono sin cerrar o con menos de 4 puntos | Valide con `validar_anillo` antes de la base (sección 5) |
| La carga con `ogr2ogr` falla con `must round to an absolute value less than 10^7` | Falta `-lco PRECISION=NO` | Agregarla (sección 4, vía B) |
| `MongoDB` o `PostGIS` rechazan `loca.json` | Es JSON de Esri, no GeoJSON, aunque el portal diga GeoJSON | Use la vía A o la vía B |
| Un punto a pocos metros de un límite entre localidades cae en la «equivocada» | Los bordes se simplificaron a ~5 m. Es el límite de precisión del dato | Para decidir *si está en Bogotá* no importa (las 20 forman una cobertura sin huecos). Para asignar localidad justo en un límite, use el dato oficial (vía B) |
| Un punto en Sumapaz cuenta como Bogotá aunque «se sienta» lejos | Sumapaz es una localidad rural enorme (781 km², el 48 % del área) que **es** Bogotá D.C. | Si solo quiere la zona urbana, excluya la localidad `20` |
| Los nombres vienen como «USAQUEN» | Vienen del dato oficial (vía B), que no tiene tildes | Use el GeoJSON preparado (vía A) o un diccionario `codigo → nombre` |

## 9. Cómo se prepararon los datos de Flota (para quien quiera reproducirlo)

`scripts/preparar_localidades.py` descarga el dato oficial, lo convierte y lo simplifica; **falla** si las localidades quedan con huecos o traslapes. Se ejecuta con Docker:

```bash
make localidades        # regenera app/data/localidades_bogota.geojson desde Datos Abiertos Bogotá
```

Flota guarda las localidades en una colección de MongoDB con índice `2dsphere` y resuelve «¿en qué localidad está este punto?» con `$geoIntersects`; las búsquedas por cercanía usan `$geoNear`. Detalle de la base en el diagrama «BD flota» de [Proyecto Rodar.drawio](Proyecto%20Rodar.drawio).

**Atribución obligatoria** (CC BY 4.0), por ejemplo en el README o en la interfaz: *«Localidades de Bogotá D.C.: Catastro Distrital / IDECA, Datos Abiertos Bogotá, CC BY 4.0.»*
