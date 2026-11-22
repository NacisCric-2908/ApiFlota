# Pendientes del API CRUD de Flota

Estado: **versión 1.0.0** terminada (rama `main`, tag `v1.0.0`; qué incluye: [CHANGELOG.md](CHANGELOG.md)). Aquí está lo que falta para que el servicio se use de verdad, ordenado por prioridad.

**Cómo usar este archivo:** marquen `[x]` al terminar, escriban su nombre como responsable y trabajen cada punto en una rama `feature/...` (ver [CONTRIBUTING.md](CONTRIBUTING.md)). Última revisión: 2026-11-22.

## 1. Bloqueantes: sin esto nadie más puede usar Flota

- [x] Subir el tag `v1.0.0` a GitHub.
- [x] Dar acceso al repositorio a los compañeros de Flota.
- [ ] **Entregar la documentación** (`docs/`) a Viajes y zonas, Cuentas y el líder del gateway **por el canal que decidan**. Las APIs son servicios independientes que se consumen por el gateway con token: **los otros equipos no clonan ni necesitan el repositorio**; el índice [docs/README.md](docs/README.md) dice qué entregar a cada uno. Responsable: ______
- [ ] **Probar contra Azure Cosmos DB real** (es el riesgo más alto: todo se probó contra MongoDB). Microsoft documenta que soporta lo que usamos (`$geoNear`, `$geoIntersects`, `$facet`, 2dsphere, `findAndModify`), pero nunca se corrió. Cómo:
  1. Crear una cuenta *Azure Cosmos DB for MongoDB (RU)*, modo **Serverless**, versión 7.0.
  2. Copiar la cadena de conexión del portal tal cual y correr las pruebas apuntando a ella: `docker compose --profile test run --rm -e MONGO_URI="<cadena>" test`. Las pruebas usan la base `flota_test` y se niegan a vaciar una base cuyo nombre no termine en `_test`.
  3. Si algo falla, anotar cuál consulta (probablemente `$geoNear`/`$facet`) y qué error da.
  Responsable: ______
- [ ] **CI/CD:** pipeline por *pull request* (correr las pruebas al abrirlo) y despliegue al fusionar, como pide el enunciado. Las pruebas ya corren con un solo comando: `docker compose --profile test run --rm --build test` (equivale a `make test`) y funcionan en un runner con Docker. Responsable: ______
- [ ] **Desplegar en Azure** según la página «Diagrama de nube» de [docs/Proyecto Rodar.drawio](docs/Proyecto%20Rodar.drawio): ACR, entorno de Container Apps **solo consumo** (no Dedicado, que cobra fijo), Cosmos DB serverless. `MONGO_URI` y `GATEWAY_SECRET` como secretos de Container Apps, nunca en la imagen. Debe quedar un **ambiente de pruebas** (con los 30 vehículos semilla) para que los otros equipos prueben su integración. Presupuesto estimado de Flota: ≈ $6 al mes. Responsable: ______
- [ ] **Datos de conexión del gateway:** completar la sección 0 de [docs/integracion.md](docs/integracion.md) (URL del gateway, ruta del token, `client_id` de cada MID) cuando el gateway esté desplegado. Responsable: ______

## 2. Gateway (a cargo del líder y su compañero)

Tareas del líder según el documento de requisitos del clúster (sección 8). Lo que necesita Flota del gateway está en [docs/integracion.md](docs/integracion.md), sección 13.

- [ ] Definir con los tres grupos los alcances y **emitir las tres credenciales** (un `client_id` por MID).
- [ ] Que `/token` funcione y que cada prefijo (`/flota`, `/cuentas`, `/viajes`) enrute al servicio correcto.
- [ ] Reglas por Flota: agregar `X-Gateway-Secret` a lo que reenvía, descartar la que traiga el cliente, quitar el prefijo `/flota`, dejar pasar los errores sin cambiarlos, responder `503` si Flota no responde y esperas de hasta 15 s en `/clima` y `/direccion`.
- [ ] Colección de pruebas (Postman o similar) que ejecute el flujo completo de la demostración (11 pasos).
- [ ] Revisar con los grupos consumidores los pull requests de contratos.
- [ ] Documentar todo en `GATEWAY.md` (quién es el líder y por qué).

## 3. MID de Flota (repositorio aparte: `ApiFlotaMID`)

**Ya está implementado:** versión 0.1.0 en la rama `develop` de ese repositorio, con `GET /recomendaciones/vehiculo` y `GET /flota/alertas`, arquitectura hexagonal, 148 pruebas, contrato OpenAPI, guía para quienes lo consumen y un simulador de los servicios de los que depende. **Se verificó contra este CRUD (1.0.0)**: mismos vehículos y mismo orden que con el simulador, y `503` si el CRUD está apagado. Su propia lista de pendientes (subirlo a GitHub, CI/CD, desplegar, probar contra Viajes y zonas real) está en el `PENDIENTES.md` de ese repositorio. Lo que sigue afecta a los dos:

- [x] La llamada del MID a su CRUD (S2S) envía `X-Gateway-Secret` (verificado).
- [ ] **Confirmar con Viajes y zonas** su `GET /zonas/verificar`: la ruta detrás del gateway (el MID usa `/viajes/zonas/verificar`), la respuesta (el MID usa solo el booleano `permitida`) y el alcance `zonas:leer`.
- [ ] **El gateway necesita reglas de prefijo distintas para las dos rutas del MID** (`/flota/recomendaciones/vehiculo` se reenvía quitando `/flota`; `/flota/alertas` se reenvía sin quitarlo). Está explicado en la sección 13 de [docs/integracion.md](docs/integracion.md). Si prefieren una regla uniforme, hay que cambiar una ruta del MID (cambio incompatible del contrato).
- [ ] **Decidir dónde viven las APIs de terceros.** Hoy están en el CRUD (`GET /vehiculos/{id}/clima` y `/direccion`) porque así se pidió; el enunciado sugiere que el consumo de un tercero esté en el MID. El MID no las usa todavía: el clima («recomendar de otra forma si llueve») quedó como idea pendiente (`ClimaPort`). El paquete `app/externos/` se puede mover tal cual.
- [ ] **Confirmar las decisiones que el enunciado no fija** (una alerta por condición, solo vehículos `disponible`, degradar en las alertas si Viajes y zonas cae): están justificadas en el `PENDIENTES.md` del MID.

## 4. Coordinar con los otros equipos

- [ ] **Viajes y zonas:** que adopten (o ajusten) las **4 zonas propuestas** de [docs/semilla.md](docs/semilla.md). Si cambian las coordenadas, mantener las propiedades que ahí se listan (dentro de Bogotá, sin traslapes, la prohibida con un vehículo recomendable pero no todos, una franja libre).
- [ ] **Viajes y zonas:** que validen el punto final de un viaje con `GET /localidades/verificar` **antes** de guardarlo como finalizado. Si no, Flota rechaza liberar el vehículo (`400 fuera_de_bogota`) y el viaje queda inconsistente. Está como «propuesto» en el flujo del `.drawio`: falta que ese grupo lo acepte.
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
