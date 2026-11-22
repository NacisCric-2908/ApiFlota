# API Flota: CRUD de Vehículos

Servicio de inventario de scooters y bicicletas del **Clúster Rodar** (grupo Flota). Guarda los vehículos en MongoDB, ofrece búsquedas geoespaciales por cercanía y está **cerrado a Bogotá D.C.** (valida cada ubicación contra las 20 localidades oficiales). El MID de Flota (recomendaciones y alertas) vive en otro repositorio.

| | |
| --- | --- |
| **Lenguaje y framework** | Python 3.12 y FastAPI |
| **Dependencias** | [uv](https://docs.astral.sh/uv/) (`pyproject.toml` y `uv.lock`) |
| **Base de datos** | MongoDB 7 (en producción puede ser Cosmos DB con API de Mongo: solo cambia `MONGO_URI`) |
| **Contrato** | [`docs/openapi.json`](docs/openapi.json) (alcances y errores declarados); con la API en marcha, también en `/docs` |
| **Todo corre en Docker** | No hace falta instalar Python, uv ni MongoDB |

## Documentación

| Para | Documento |
| --- | --- |
| **Consumir la API** (otros grupos): autenticación, endpoints, recetas, errores, ejemplos en Python y Java | [docs/integracion.md](docs/integracion.md) |
| APIs de terceros: fichas, límites, caché, plan de degradación | [docs/terceros.md](docs/terceros.md) |
| Manejo geoespacial y localidades de Bogotá | [docs/geoespacial.md](docs/geoespacial.md) |
| Los 30 vehículos semilla (para coordinar zonas con Viajes y zonas) | [docs/semilla.md](docs/semilla.md) |
| **Diagramas del proyecto** (nube en Azure con costos, flujo general, arquitectura hexagonal y base de datos; documento conjunto con los otros grupos) | [docs/Proyecto Rodar.drawio](docs/Proyecto%20Rodar.drawio) (abrir con diagrams.net) |
| Cómo trabajar en este repo (git flow, commits, uv, pruebas) | [CONTRIBUTING.md](CONTRIBUTING.md) |

## Ejecución

```bash
cp .env.example .env     # opcional: sin .env se usan valores de desarrollo
make up                  # equivale a: docker compose up -d --build
curl localhost:8000/health
curl -H "X-Gateway-Secret: cambiar-este-secreto" "localhost:8000/vehiculos?lat=4.711&lng=-74.0721&radioMetros=300&estado=disponible"
```

`docker compose up` aplica `docker-compose.override.yml` (recarga en caliente). Para un entorno tipo producción: `docker compose -f docker-compose.yml up -d`. Al arrancar con la colección vacía se cargan 30 vehículos semilla (`SEED_ON_EMPTY=true`); para reiniciarlos: `docker compose down -v`.

## Pruebas

```bash
make test                # equivale a: docker compose --profile test run --rm --build test
```

Corren contra un MongoDB real (base `flota_test`, que se vacía en cada prueba), así se verifican de verdad los índices 2dsphere, `$geoIntersects` y la reserva atómica de vehículos. **Nunca salen a internet:** las APIs de terceros se simulan. Hay pruebas que fallan si `docs/openapi.json` o `docs/semilla.md` quedan desactualizados.

## Endpoints

Todos usan el formato de error `{ "codigo": "...", "mensaje": "...", "detalle": {} }`; los datos inválidos responden 400. Detalle y ejemplos en [docs/integracion.md](docs/integracion.md).

| Método y ruta | Qué hace | Alcance | Códigos |
| --- | --- | --- | --- |
| `GET /vehiculos` | Lista con filtros `tipo`, `estado`, `localidad`, `bateriaMin`, cercanía (`lat`, `lng`, `radioMetros`) y paginación | `vehiculos:leer` | 200, 400 |
| `GET /vehiculos/{id}` | Detalle | `vehiculos:leer` | 200, 404 |
| `POST /vehiculos` | Crea un vehículo (`id` opcional) | `vehiculos:escribir` | 201, 400, 409 |
| `PUT /vehiculos/{id}` | Reemplaza un vehículo | `vehiculos:escribir` | 200, 400, 404 |
| `PATCH /vehiculos/{id}/estado` | Cambia estado y, opcionalmente, ubicación y batería (**atómico**) | `vehiculos:escribir` | 200, 400, 404, 409 |
| `DELETE /vehiculos/{id}` | Elimina (no si está `en_viaje`) | `vehiculos:escribir` | 204, 404, 409 |
| `GET /localidades` | Las 20 localidades con el conteo de vehículos | `vehiculos:leer` | 200 |
| `GET /localidades/verificar?lat&lng` | ¿En qué localidad está un punto? | `vehiculos:leer` | 200, 400 |
| `GET /localidades/{codigo}` | Una localidad con su geometría (GeoJSON) | `vehiculos:leer` | 200, 404 |
| `GET /vehiculos/{id}/clima` | Clima en la ubicación del vehículo (Open-Meteo) | `vehiculos:leer` | 200, 404, 503 |
| `GET /vehiculos/{id}/direccion` | Dirección de la ubicación (Nominatim/OSM) | `vehiculos:leer` | 200, 404, 503 |
| `GET /health` | Salud del servicio (público) | n/a | 200 |

Reglas de diseño que conviene conocer:

- **Cerrado a Bogotá:** una ubicación fuera de las 20 localidades responde `400 fuera_de_bogota`. La `localidad` de cada vehículo la calcula el servicio.
- **Coordenadas:** GeoJSON `[longitud, latitud]`; en parámetros de consulta, `lat` y `lng`.
- **Cercanía:** `lat` y `lng` van juntas; `radioMetros` vale 500 si se omite. El resultado va del más cercano al más lejano con `distanciaMetros`.
- **Transiciones de estado:** `disponible` → `en_viaje` o `mantenimiento`; `en_viaje` → `disponible` o `mantenimiento`; `mantenimiento` → `disponible`. Repetir el estado actual responde 409. El cambio es una única operación condicional en MongoDB: si dos peticiones compiten por el mismo vehículo, solo una gana.
- **Seguridad:** los alcances los valida el API Gateway. Este servicio rechaza con 401 toda petición sin la cabecera `X-Gateway-Secret` correcta (excepto `/health`, `/docs` y `/openapi.json`).

## Ficha de las APIs de terceros

Ambas son gratuitas y no requieren llave. Fichas completas, límites y plan de degradación en [docs/terceros.md](docs/terceros.md).

| | Open-Meteo | Nominatim (OpenStreetMap) |
| --- | --- | --- |
| Uso | Clima actual donde está un vehículo | Dirección legible de una ubicación |
| Espera máxima / reintentos | 3 s / 2 | 3 s / 2 |
| Caché | 10 min | 24 h |
| Si falla | Último dato guardado (hasta 3 h) o 503 | Último dato guardado (hasta 7 días) o la localidad del vehículo |

Los datos de las localidades de Bogotá vienen de [Datos Abiertos Bogotá](https://datosabiertos.bogota.gov.co/dataset/localidad-bogota-d-c) (Catastro Distrital / IDECA, CC BY 4.0).

## Variables de entorno

Ver [`.env.example`](.env.example). Las sensibles (`MONGO_URI`, `GATEWAY_SECRET`) no tienen valor por defecto en la aplicación: si faltan, no arranca. Las de los terceros tienen valores por defecto que sirven.

## Atajos (`make`)

| Comando | Qué hace |
| --- | --- |
| `make up` / `make down` / `make logs` | Levanta, detiene y sigue los logs |
| `make test` | Pruebas |
| `make add pkg=httpx` | Agrega una dependencia con uv (dev: `pkg="--dev pytest-cov"`) |
| `make lock` | Re-resuelve `uv.lock` |
| `make openapi` | Regenera `docs/openapi.json` |
| `make docs-semilla` | Regenera `docs/semilla.md` |
| `make localidades` | Regenera el GeoJSON de localidades desde Datos Abiertos Bogotá |

## Aportes de cada integrante

_Pendiente: completar con el nombre de cada integrante y su aporte._
