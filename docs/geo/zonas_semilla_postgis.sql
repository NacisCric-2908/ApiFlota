-- Zonas semilla que Flota propone a Viajes y zonas (1 prohibida, 1 de recargo, 2 de parqueo).
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
    ('Prohibida Centro', 'prohibida',
     ST_SetSRID(ST_GeomFromGeoJSON('{"type": "Polygon", "coordinates": [[[-74.0719, 4.7107], [-74.0714, 4.7107], [-74.0714, 4.7113], [-74.0719, 4.7113], [-74.0719, 4.7107]]]}'), 4326)),
    ('Recargo Oriente', 'recargo',
     ST_SetSRID(ST_GeomFromGeoJSON('{"type": "Polygon", "coordinates": [[[-74.071, 4.7086], [-74.0694, 4.7086], [-74.0694, 4.7134], [-74.071, 4.7134], [-74.071, 4.7086]]]}'), 4326)),
    ('Parqueo Occidente', 'parqueo',
     ST_SetSRID(ST_GeomFromGeoJSON('{"type": "Polygon", "coordinates": [[[-74.0748, 4.7086], [-74.073, 4.7086], [-74.073, 4.7134], [-74.0748, 4.7134], [-74.0748, 4.7086]]]}'), 4326)),
    ('Parqueo Sur', 'parqueo',
     ST_SetSRID(ST_GeomFromGeoJSON('{"type": "Polygon", "coordinates": [[[-74.073, 4.7086], [-74.071, 4.7086], [-74.071, 4.71], [-74.073, 4.71], [-74.073, 4.7086]]]}'), 4326));

-- Comprobación: todas las zonas deben quedar dentro de Bogotá (debe devolver 0 filas).
SELECT z.nombre AS zona_fuera_de_bogota
FROM zonas z, bogota b
WHERE NOT ST_CoveredBy(z.poligono, b.geom);
