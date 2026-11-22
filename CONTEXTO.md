# Contexto para continuar el trabajo en un chat nuevo

Pegue o pida leer este archivo al empezar. Resume dónde quedó todo (2026-11-22). Detalles: `PENDIENTES.md`, `CHANGELOG.md`, `docs/README.md` y el `.drawio`.

## Proyecto
Clúster **Rodar** (scooters y bicicletas compartidas), materia Desarrollo Web Backend. Tres grupos: **Flota** (nosotros, MongoDB), Cuentas (PostgreSQL, Java/Spring o Python) y Viajes y zonas (PostgreSQL + PostGIS, Python/FastAPI). Cada grupo: un CRUD + un MID, contrato OpenAPI, un API de tercero. Requisitos del clúster: `X1.cluster-rodar.md` (este repo). El enunciado general no se ha visto.
**Principio acordado:** las APIs son servicios independientes en la nube, consumidos con token por el gateway. **Nadie clona repos ajenos** para usarlas; la documentación se entrega sin repositorio.

## Repos (locales en /home/naciscric/Documentos/)
| Repo | Estado |
| --- | --- |
| `ApiFlota` (CRUD de vehículos) | **1.0.0** en `main`, tag `v1.0.0`; `develop` al día; subido a GitHub. 150 pruebas |
| `ApiFlotaMID` | **0.1.0** en `develop` (sin release, `main` solo con commit inicial), **solo local, sin subir**. 148 pruebas |
Ambos: Python 3.12 + FastAPI, uv, **todo en Docker** (`make up`, `make test`, `make openapi`, `make lock`), git flow con microcommits en español (Conventional Commits), ramas `feature/*` fusionadas con `--no-ff`, **sin Co-Authored-By** (memoria del usuario). El usuario pondrá en horas reglas de rama en `main` y flujo con PRs: desde entonces ya no se commitea directo a `main`/`develop`.

## Qué hay construido
- **CRUD Flota:** 6 endpoints de vehículos (reserva atómica con `find_one_and_update`), cercanía 2dsphere, **cerrado a Bogotá** con las 20 localidades oficiales (`/localidades`, `/verificar`, `/{codigo}`; dato sin huecos, `coverage_simplify`), clima (Open-Meteo) y dirección (Nominatim) con reintentos/caché/degradación, 30 vehículos semilla (centro lat 4.7110, lng -74.0721, en Suba), `X-Gateway-Secret`, OpenAPI 3.1 con `operationId` limpios.
- **MID Flota:** hexagonal. `GET /recomendaciones/vehiculo` (500 m, ≥25 %, sin zona prohibida, puntaje = distancia − batería×2, 3 mejores, 503 si Viajes y zonas cae) y `GET /flota/alertas` (una alerta por condición, solo `disponible`, degrada con `zonas_no_verificadas`). MID→CRUD directo (S2S con el secreto del CRUD); MID→Viajes y zonas **por el gateway** con token OAuth client credentials (`TokenGateway`). Simulador de CRUD/zonas/token en `simuladores/`. **Verificado contra el CRUD real.**
- **Docs** (`ApiFlota/docs/`): `integracion.md`, `geoespacial.md` (recetas verificadas en PostGIS), `semilla.md` (incluye 4 zonas propuestas para Viajes y zonas y resultados esperados), `geo/*.sql`, `terceros.md`, `openapi.json`, `Proyecto Rodar.drawio` (nuestras páginas: nube Azure con costos, flujo general, hexagonal, BD). Un test falla si docs/contrato se desactualizan. MID: `docs/integracion.md` propio.

## Decisiones tomadas
- Alertas: una por condición; solo `disponible`; prioridades `alta` (<10 % batería o zona prohibida) / `media`. Alertas degradan si Viajes y zonas cae; la recomendación da 503.
- Alcances propuestos MID: `recomendaciones:leer`, `alertas:leer`; la credencial del MID necesita `zonas:leer`. CRUD: `vehiculos:leer|escribir`.
- Rutas MID en el gateway con reglas de prefijo **distintas**: `/flota/recomendaciones/vehiculo`→`/recomendaciones/vehiculo` (quita `/flota`); `/flota/alertas`→`/flota/alertas` (no quita). CRUD: `/flota/*`→`/*`.
- Presupuesto Azure Flota ≈ $6/mes (Cosmos DB for MongoDB serverless, Container Apps solo consumo con mínimo 0 réplicas, ACR Basic). Cosmos **no probado** con las consultas reales.

## Siguiente tarea: el gateway propio
Decidido: **gateway propio en contenedor en Azure Container Apps** (no Raspberry+Cloudflare: punto único de falla, latencia, URL estable exige dominio; ni APIM, que no emite tokens propios). Lo hacen el usuario y un compañero de Flota (líder del gateway). Tareas del enunciado (sección 8): definir alcances y emitir una credencial por MID; `/token` funcionando; enrutar `/flota`, `/cuentas`, `/viajes`; colección Postman con el flujo de 11 pasos (sección 9); revisar PRs de contratos; documentar en `GATEWAY.md`. Elegir producto (Kong/APISIX/Traefik en YAML) o código propio (FastAPI).
**Lo que Flota espera del gateway** (ya documentado en `ApiFlota/docs/integracion.md` §13 y MID §2): validar token y alcances; agregar `X-Gateway-Secret` por servicio y descartar la del cliente; quitar prefijo según tabla; pasar errores `{codigo,mensaje,detalle}` sin cambiar; 503 con ese formato si el servicio no responde; esperas ≥15 s; `/token` OAuth2 client credentials (POST form: grant_type, client_id, client_secret, scope → `access_token`, `expires_in`); demo: sin credenciales 401, sin alcance 403.

## Pendientes principales (ver PENDIENTES.md de cada repo)
Subir el MID a GitHub; CI/CD y reglas de rama; desplegar en Azure con ambiente de pruebas; probar contra Cosmos real, Viajes y zonas real y el token real; confirmar con Viajes y zonas sus rutas/respuesta (`/zonas/verificar`, `permitida`); que adopten las zonas propuestas y validen el punto final con `/localidades/verificar`; completar la sección 0 de `docs/integracion.md` (URL, token, client_ids); entregar docs a los otros equipos; «Aportes de cada integrante» en los READMEs; decidir dónde viven las APIs de terceros (hoy en el CRUD).

## Trampas aprendidas
- Contenedores con `-v` de la carpeta temporal necesitan `--user $(id -u):$(id -g)`.
- `docker run`/`pkill -f` con patrones propios pueden matar la propia shell; el visor de diagramas se sirvió con `python3 -m http.server` local.
- `jq` sin `-c` rompe el cargador SQL de localidades; `ogr2ogr` necesita `-lco PRECISION=NO`.
- Hay un archivo sin seguimiento del usuario, `guiaCD.md`, que no se debe tocar ni commitear.
