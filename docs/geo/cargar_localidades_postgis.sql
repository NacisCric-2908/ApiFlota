-- Carga las 20 localidades de Bogotá D.C. en PostGIS (sin GDAL ni ogr2ogr: solo psql).
--
-- Uso (desde la carpeta que contiene localidades_bogota.geojson):
--     psql "$DATABASE_URL" -f cargar_localidades_postgis.sql
--
-- El archivo localidades_bogota.geojson está en este repositorio: app/data/localidades_bogota.geojson
-- Es idempotente: se puede ejecutar varias veces.

CREATE EXTENSION IF NOT EXISTS postgis;

DROP TABLE IF EXISTS bogota;
DROP TABLE IF EXISTS localidades CASCADE;

CREATE TABLE localidades (
    codigo  text PRIMARY KEY,                       -- '01' a '20' (código oficial)
    nombre  text    NOT NULL,                       -- 'La Candelaria'
    area_m2 integer NOT NULL,
    geom    geometry(MultiPolygon, 4326) NOT NULL   -- WGS84, longitud/latitud
);
CREATE INDEX localidades_geom_gix ON localidades USING GIST (geom);

-- El GeoJSON viene en una sola línea: se lee como un único valor jsonb.
CREATE TEMP TABLE crudo (doc jsonb);
\copy crudo FROM 'localidades_bogota.geojson' WITH (FORMAT csv, QUOTE E'\x01', DELIMITER E'\x02')

INSERT INTO localidades (codigo, nombre, area_m2, geom)
SELECT f -> 'properties' ->> 'codigo',
       f -> 'properties' ->> 'nombre',
       (f -> 'properties' ->> 'areaM2')::integer,
       ST_SetSRID(ST_GeomFromGeoJSON(f ->> 'geometry'), 4326)
FROM crudo, jsonb_array_elements(doc -> 'features') AS f;

-- Contorno de Bogotá: la unión de las 20 localidades. Sirve para validar que una zona queda dentro de la ciudad.
CREATE TABLE bogota AS
SELECT ST_Multi(ST_Union(geom))::geometry(MultiPolygon, 4326) AS geom FROM localidades;
CREATE INDEX bogota_geom_gix ON bogota USING GIST (geom);

SELECT count(*) AS localidades_cargadas, bool_and(ST_IsValid(geom)) AS todas_validas FROM localidades;
