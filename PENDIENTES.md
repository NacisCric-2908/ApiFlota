# Pendientes del API CRUD de Flota

Estado: **versión 1.0.0** terminada (rama `main`, tag `v1.0.0`; qué incluye: [CHANGELOG.md](CHANGELOG.md)). Aquí está lo que falta para que el servicio se use de verdad, ordenado por prioridad.

**Cómo usar este archivo:** marquen `[x]` al terminar, escriban su nombre como responsable y trabajen cada punto en una rama `feature/...` (ver [CONTRIBUTING.md](CONTRIBUTING.md)). Última revisión: 2026-11-22.

## 1. Bloqueantes: sin esto nadie más puede usar Flota

- [ ] **Subir el tag a GitHub.** El tag `v1.0.0` existe solo en local; en GitHub están las ramas pero no el tag. `git push origin v1.0.0`. Responsable: ______
- [ ] **Dar acceso al repositorio** a Viajes y zonas y a Cuentas (o enviarles `docs/` y `app/data/localidades_bogota.geojson`). Después, reemplazar `<repo>` en [docs/integracion.md](docs/integracion.md) (sección 9, `git clone <repo>`) por la URL de GitHub. Responsable: ______
- [ ] **Probar contra Azure Cosmos DB real** (es el riesgo más alto: todo se probó contra MongoDB). Microsoft documenta que soporta lo que usamos (`$geoNear`, `$geoIntersects`, `$facet`, 2dsphere, `findAndModify`), pero nunca se corrió. Cómo:
  1. Crear una cuenta *Azure Cosmos DB for MongoDB (RU)*, modo **Serverless**, versión 7.0.
  2. Copiar la cadena de conexión del portal tal cual y correr las pruebas apuntando a ella: `docker compose --profile test run --rm -e MONGO_URI="<cadena>" test`. Las pruebas usan la base `flota_test` y se niegan a vaciar una base cuyo nombre no termine en `_test`.
  3. Si algo falla, anotar cuál consulta (probablemente `$geoNear`/`$facet`) y qué error da.
  Responsable: ______
- [ ] **CI/CD:** pipeline por *pull request* (correr las pruebas al abrirlo) y despliegue al fusionar, como pide el enunciado. Las pruebas ya corren con un solo comando: `docker compose --profile test run --rm --build test` (equivale a `make test`) y funcionan en un runner con Docker. Responsable: ______
- [ ] **Desplegar en Azure** según la página «Diagrama de nube» de [docs/Proyecto Rodar.drawio](docs/Proyecto%20Rodar.drawio): ACR, entorno de Container Apps **solo consumo** (no Dedicado, que cobra fijo), Cosmos DB serverless. `MONGO_URI` y `GATEWAY_SECRET` como secretos de Container Apps, nunca en la imagen. Presupuesto estimado de Flota: ≈ $6 al mes. Responsable: ______
- [ ] **Datos de conexión del gateway:** completar la sección 0 de [docs/integracion.md](docs/integracion.md) (URL del gateway, ruta del token, `client_id` de cada MID) cuando el gateway esté desplegado. Responsable: ______

## 2. Gateway (a cargo del líder y su compañero)

Tareas del líder según el documento de requisitos del clúster (sección 8). Lo que necesita Flota del gateway está en [docs/integracion.md](docs/integracion.md), sección 13.

- [ ] Definir con los tres grupos los alcances y **emitir las tres credenciales** (un `client_id` por MID).
- [ ] Que `/token` funcione y que cada prefijo (`/flota`, `/cuentas`, `/viajes`) enrute al servicio correcto.
- [ ] Reglas por Flota: agregar `X-Gateway-Secret` a lo que reenvía, descartar la que traiga el cliente, quitar el prefijo `/flota`, dejar pasar los errores sin cambiarlos, responder `503` si Flota no responde y esperas de hasta 15 s en `/clima` y `/direccion`.
- [ ] Colección de pruebas (Postman o similar) que ejecute el flujo completo de la demostración (11 pasos).
- [ ] Revisar con los grupos consumidores los pull requests de contratos.
- [ ] Documentar todo en `GATEWAY.md` (quién es el líder y por qué).

## 3. MID de Flota (repositorio aparte)

Todavía no existe. Mismo método de trabajo: git flow con microcommits, Docker, Python + FastAPI, uv. Su diseño está en la página «Hexagonal - Flota» del `.drawio`.

- [ ] Crear el repositorio y copiar la estructura base (Dockerfile, compose, `Makefile`, `.env.example`, `/health`, rechazo sin la cabecera del gateway).
- [ ] `GET /recomendaciones/vehiculo?lat&lng&tipo`: radio 500 m, batería de al menos 25 %, descartar zona prohibida (consulta a Viajes y zonas), `puntaje = distancia − batería × 2`, 3 mejores, `motivo` si no hay candidatos, `503` si Viajes y zonas no responde. **El resultado esperado con los datos semilla está en [docs/semilla.md](docs/semilla.md)** (veh-0014, veh-0022, veh-0008).
- [ ] `GET /flota/alertas`: batería menor a 15 %, zona prohibida o más de 2 h sin actualizar, con `tipoAlerta` y `prioridad`.
- [ ] Contrato OpenAPI, pruebas unitarias con simulación de los demás servicios y de los terceros, pipeline y README con la ficha del API de tercero.
- [ ] La llamada del MID a su CRUD (S2S) debe enviar `X-Gateway-Secret`.
- [ ] **Decidir dónde viven las APIs de terceros.** Hoy están en el CRUD (`GET /vehiculos/{id}/clima` y `/direccion`) porque así se pidió; el enunciado sugiere que el consumo de un tercero esté en el MID. El paquete `app/externos/` se puede mover tal cual.

## 4. Coordinar con los otros equipos

- [ ] **Viajes y zonas:** que adopten (o ajusten) las **4 zonas propuestas** de [docs/semilla.md](docs/semilla.md). Si cambian las coordenadas, mantener las propiedades que ahí se listan (dentro de Bogotá, sin traslapes, la prohibida con un vehículo recomendable pero no todos, una franja libre).
- [ ] **Viajes y zonas:** que validen el punto final de un viaje con `GET /localidades/verificar` **antes** de guardarlo como finalizado. Si no, Flota rechaza liberar el vehículo (`400 fuera_de_bogota`) y el viaje queda inconsistente. Está como «propuesto» en el flujo del `.drawio`: falta que ese grupo lo acepte.
- [ ] **Entregar la documentación** a cada equipo: el índice [docs/README.md](docs/README.md) dice qué leer según el rol.
- [ ] **Nominatim lo usan dos grupos** (Flota para la dirección, Viajes y zonas para geocodificar). Su límite es 1 petición por segundo; cada servicio usa su propio `User-Agent`, pero conviene que lo sepan.
- [ ] Confirmar con los demás grupos el formato de error común del clúster (`{codigo, mensaje, detalle}`).

## 5. Mejoras del CRUD (no bloqueantes; varias son decisiones del grupo)

- [ ] **`/docs` y `/openapi.json` son públicos** (sin la cabecera del gateway). Decidir si se exponen en producción.
- [ ] **`/health` solo indica que el proceso está vivo**, no consulta MongoDB. Para el *probe* de Container Apps conviene un *readiness* que haga ping a la base.
- [ ] **Logs estructurados y métricas.** Hoy solo hay el registro por defecto de uvicorn. En Azure irían a Log Analytics (5 GB gratis al mes).
- [ ] **`GATEWAY_SECRET` de desarrollo** (`cambiar-este-secreto`) viene por defecto en `docker-compose.yml`. Decidir si la aplicación debe negarse a arrancar con ese valor fuera de desarrollo.
- [ ] **Caché y límite de tasa de los terceros viven en memoria de cada réplica.** Si se escala a varias réplicas, el límite de Nominatim aplica por réplica; considerar una caché compartida (Redis).
- [ ] **Linter y formateador** (por ejemplo `ruff`) y medición de cobertura en el pipeline.
- [ ] **La reserva de un vehículo no es idempotente** (limitación conocida y documentada): repetir el `PATCH` a `en_viaje` da `409` aunque la primera vez haya funcionado. Evaluar un identificador de reserva si el MID de Viajes lo necesita (sería un cambio compatible).
- [ ] **Costos:** ACR por grupo suma ≈ $15 al mes entre los tres; uno compartido, o GitHub Container Registry, ahorraría ≈ $10 de los $100. Verificar también que la región elegida esté permitida en Azure for Students.

## 6. Documentación

- [ ] Completar **«Aportes de cada integrante»** en el [README.md](README.md).
- [ ] Revisar el `.drawio` abriéndolo en diagrams.net (se revisó con un visor, no con la aplicación de escritorio).
- [ ] Cada vez que cambie el contrato: `make openapi`, `make docs-semilla` si cambió la semilla, subir la versión (`pyproject.toml` y `app/main.py` deben coincidir; hay una prueba que lo verifica) y anotar el cambio en [CHANGELOG.md](CHANGELOG.md). Los cambios incompatibles suben la versión **mayor** y se avisan a los grupos consumidores antes.

## Comandos útiles

| Comando | Qué hace |
| --- | --- |
| `make up` / `make down` | Levanta y detiene la API con MongoDB |
| `make test` | Pruebas contra un MongoDB real (150) |
| `make openapi` | Regenera `docs/openapi.json` |
| `make docs-semilla` | Regenera `docs/semilla.md` y `docs/geo/zonas_semilla_postgis.sql` |
| `make localidades` | Regenera el GeoJSON de las localidades desde Datos Abiertos Bogotá |
| `make add pkg=...` / `make lock` | Dependencias con uv |
