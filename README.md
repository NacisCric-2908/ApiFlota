# API Flota: CRUD de Vehículos

Servicio de inventario de scooters y bicicletas del **Clúster Rodar** (grupo Flota). Guarda los vehículos en MongoDB y expone búsquedas geoespaciales por cercanía. El MID de Flota (recomendaciones y alertas) vive en otro repositorio.

- **Lenguaje y framework:** Python 3.12 y FastAPI.
- **Base de datos:** MongoDB 7 (en producción puede ser Cosmos DB con API de Mongo: solo cambia `MONGO_URI`).
- **Contrato:** [`docs/openapi.json`](docs/openapi.json) (alcances y errores declarados). Con la API en marcha también está en `/docs`.
- Todo corre en Docker; no hace falta instalar Python ni MongoDB.

## Ejecución

```bash
cp .env.example .env     # opcional: sin .env se usan valores de desarrollo
make up                  # equivale a: docker compose up -d --build
curl localhost:8000/health
curl -H "X-Gateway-Secret: cambiar-este-secreto" "localhost:8000/vehiculos?lat=4.711&lng=-74.072&radioMetros=300&estado=disponible"
```

`docker compose up` aplica `docker-compose.override.yml` (recarga en caliente). Para un entorno tipo producción: `docker compose -f docker-compose.yml up -d`.

Al arrancar con la colección vacía se cargan 30 vehículos semilla (`SEED_ON_EMPTY=true`).

## Pruebas

```bash
make test                # equivale a: docker compose --profile test run --rm --build test
```

Corren contra un MongoDB real (base `flota_test`, que se vacía en cada prueba), así se verifican de verdad el índice 2dsphere y la reserva atómica de vehículos.

## Endpoints

| Método y ruta | Qué hace | Alcance | Códigos |
| --- | --- | --- | --- |
| `GET /vehiculos` | Lista con filtros `tipo`, `estado`, `bateriaMin`, cercanía (`lat`, `lng`, `radioMetros`) y paginación (`pagina`, `tamano`) | `vehiculos:leer` | 200, 400 |
| `GET /vehiculos/{id}` | Detalle | `vehiculos:leer` | 200, 404 |
| `POST /vehiculos` | Crea un vehículo (`id` opcional) | `vehiculos:escribir` | 201, 400, 409 |
| `PUT /vehiculos/{id}` | Reemplaza un vehículo | `vehiculos:escribir` | 200, 400, 404 |
| `PATCH /vehiculos/{id}/estado` | Cambia estado y, opcionalmente, ubicación y batería (atómico) | `vehiculos:escribir` | 200, 400, 404, 409 |
| `DELETE /vehiculos/{id}` | Elimina (no si está `en_viaje`) | `vehiculos:escribir` | 204, 404, 409 |
| `GET /health` | Salud del servicio (sin cabecera del gateway) | n/a | 200 |

Notas de diseño:

- **Coordenadas:** GeoJSON, en orden `[longitud, latitud]`. En los parámetros de consulta se usa `lat` y `lng` por separado.
- **Cercanía:** `lat` y `lng` van juntas; `radioMetros` vale 500 si se omite. El resultado va del más cercano al más lejano e incluye `distanciaMetros`.
- **Transiciones de estado:** `disponible` → `en_viaje` o `mantenimiento`; `en_viaje` → `disponible` o `mantenimiento`; `mantenimiento` → `disponible`. Repetir el estado actual responde 409. El cambio es una única operación condicional en MongoDB: si dos peticiones compiten por el mismo vehículo, solo una gana.
- **Errores:** siempre `{ "codigo": "...", "mensaje": "...", "detalle": {} }`. Los datos inválidos responden 400.
- **Seguridad:** los alcances los valida el API Gateway. Este servicio rechaza con 401 toda petición sin la cabecera `X-Gateway-Secret` correcta (excepto `/health`, `/docs` y `/openapi.json`).

## Datos semilla (acordar con Viajes y zonas)

30 vehículos en una cuadrícula de 6 x 5 (separación de ~100 m) centrada en **lat 4.7110, lng -74.0721** (Plaza de Bolívar, Bogotá). Todos quedan a menos de ~350 m del centro. Las zonas que siembre el grupo de Viajes y zonas deben cubrir esa misma área. Hay variedad intencional de batería (bajo 25 %, bajo 15 % y bajo 10 %), de estados y de antigüedad de la ubicación para poder probar el MID. Ver [`app/db/semilla.py`](app/db/semilla.py).

## Variables de entorno

Ver [`.env.example`](.env.example). Las sensibles (`MONGO_URI`, `GATEWAY_SECRET`) no tienen valor por defecto en la aplicación: si faltan, no arranca.

## Metodología

Git flow con microcommits: `main` (versiones), `develop` (integración) y una rama `feature/*` por bloque de trabajo, fusionada a `develop` con `--no-ff`.

## Aportes de cada integrante

_Pendiente: completar con el nombre de cada integrante y su aporte._
