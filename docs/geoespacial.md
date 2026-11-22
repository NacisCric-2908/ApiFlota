# Manejo geoespacial: servicio cerrado a Bogotá D.C.

El servicio solo acepta vehículos dentro de Bogotá. Se delimita con las **20 localidades** oficiales (datos abiertos), que además permiten saber en qué localidad está cada vehículo.

## Cómo funciona

1. Al arrancar se cargan las 20 localidades en la colección `localidades` de MongoDB, con índice **2dsphere** sobre su geometría (`MultiPolygon`). La carga es idempotente (se puede arrancar muchas veces).
2. Al **crear**, **reemplazar** o **mover** un vehículo (`PATCH .../estado` con `ubicacion`), el servicio busca la localidad con `$geoIntersects`. Si no hay ninguna: `400 fuera_de_bogota`. Si hay: se guarda `localidad` en el vehículo.
3. Las búsquedas por cercanía usan `$geoNear` sobre el índice 2dsphere de `vehiculos.ubicacion`, con distancias esféricas en metros.
4. Si arranca con vehículos guardados antes de existir el campo `localidad`, se les asigna automáticamente.

## Convenciones

- Orden de coordenadas: `[longitud, latitud]` (GeoJSON). Parámetros de consulta: `lat` y `lng`.
- Sistema de referencia: WGS84 (el original está en MAGNA-SIRGAS geográfico; la diferencia es de centímetros, irrelevante aquí).
- Un punto sobre el borde entre dos localidades cuenta como dentro de ambas; el servicio devuelve una de ellas.
- Sumapaz es una localidad rural enorme (781 km², el 48 % del área total). Un punto allí es «Bogotá» aunque esté lejos de la ciudad.

## Para el grupo de Viajes y zonas

- Sus zonas (prohibida, recargo, parqueo) deben quedar dentro de Bogotá y cubrir el área de los vehículos semilla: ver [semilla.md](semilla.md).
- `GET /localidades/{codigo}` devuelve la geometría de una localidad como Feature GeoJSON. Sirve de base para diseñar zonas o para verificar que un polígono está dentro de Bogotá.
- `GET /localidades/verificar?lat&lng` indica si un punto está en Bogotá. Úsenlo para validar el punto final **antes** de guardar un viaje como finalizado (ver la receta en [integracion.md](integracion.md)).

## El archivo de datos

`app/data/localidades_bogota.geojson` (137 KB) lo genera `scripts/preparar_localidades.py` a partir del dataset oficial:

```bash
make localidades     # descarga, repara, simplifica y reescribe el GeoJSON (corre en Docker)
```

El script convierte el JSON de Esri del original a GeoJSON válido para MongoDB (geometrías reparadas, anillos exteriores antihorarios), lo simplifica a ~5 m de tolerancia, redondea a 5 decimales (~1 m) y pone los nombres oficiales con tildes (el original los trae en mayúsculas y sin tildes). Al ser tan pequeño, se versiona en el repositorio: el servicio arranca sin depender de internet.

Fuente y licencia: ver [terceros.md](terceros.md#datos-abiertos-localidades-de-bogotá).
