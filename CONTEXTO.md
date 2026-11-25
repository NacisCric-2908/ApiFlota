# Contexto para continuar el trabajo en un chat nuevo

Pegue o pida leer este archivo al empezar. Resume dónde quedó todo (2026-11-25). Detalles: `PENDIENTES.md`, `CHANGELOG.md`, `docs/README.md` y el `.drawio`.

## Proyecto
Clúster **Rodar** (scooters y bicicletas compartidas), materia Desarrollo Web Backend. Tres grupos: **Flota** (nosotros, MongoDB), Cuentas (PostgreSQL, Java/Spring o Python) y Viajes y zonas (PostgreSQL + PostGIS, Python/FastAPI). Cada grupo: un CRUD + un MID, contrato OpenAPI, un API de tercero. Requisitos del clúster: `X1.cluster-rodar.md` (este repo). El enunciado general no se ha visto.
**Principio acordado:** las APIs son servicios independientes en la nube, consumidos con token por el gateway. **Nadie clona repos ajenos** para usarlas; la documentación se entrega sin repositorio.

## Repos (locales en /home/naciscric/Documentos/)
| Repo | Estado |
| --- | --- |
| `ApiFlota` (CRUD de vehículos) | **1.0.0** en `main`, tag `v1.0.0`; `develop` al día; subido a GitHub. 150 pruebas |
| `ApiFlotaMID` | **0.1.0** en `develop` (sin release, `main` solo con commit inicial), **solo local, sin subir**. 148 pruebas. Rama `feature/despliegue-azure` con Bicep + CI/CD + guía |
| `ApiWategay` (gateway; el nombre de la carpeta es un typo del usuario, se conserva) | KrakenD 3 + servicio de tokens propio (FastAPI, JWT RS256, OAuth2 client credentials). 30 pruebas de tokens + 168 e2e por el gateway. **Solo local.** Rama `feature/despliegue-azure` con Bicep (tokens interno + gateway público), CI/CD, `scripts/03-secretos-produccion.sh`, README, `GATEWAY.md`, `docs/` (consumo, operación, rutas generadas, Postman) |
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

## Estado: todo el código de despliegue a Azure está escrito, NADA se ha ejecutado en Azure
Los tres repos tienen `infra/*.bicep`, `.github/workflows/{ci,cd}.yml` (CD con OIDC `azure/login@v2`, ejecutores de GitHub, sin contraseñas guardadas) y su `docs/despliegue-azure.md`. **La guía principal está en `ApiFlota/docs/despliegue-azure.md`.** Diseño: un grupo `rg-rodar`; ACR Basic; entorno de Container Apps solo consumo; Cosmos DB for MongoDB serverless (7.0); solo `rodar-gateway` con ingreso público, `rodar-tokens`, `flota-mid` y `flota-crud` internos; direcciones predecibles `https://<app>.internal.<dominioDelEntorno>`; réplicas mínimas 0 (arranque en frío → `infra/scripts/modo-demo.sh encendido|ahorro`).
Una sola vez: `ApiFlota/infra/scripts/01-plataforma.sh` → `02-acceso-github.sh` (OIDC por repo, solo rama `main`) → `ApiWategay/scripts/03-secretos-produccion.sh` (genera llaves/secretos en `secretos-produccion/`, ignorado por git, y los publica con `gh secret set` en los tres repos). Primer despliegue en orden: ApiFlota → ApiFlotaMID → ApiWategay. Secretos por repo: CRUD `FLOTA_CRUD_SECRET`; MID `FLOTA_MID_SECRET`, `FLOTA_CRUD_SECRET`, `MID_FLOTA_CLIENT_SECRET`; gateway `JWT_PRIVATE_KEY_B64`, `CLIENTES_JSON`, `JWKS_JSON` y los seis `*_SECRET`.
**Tokens:** el servicio propio emite JWT RS256; los mismos binarios corren en local y Azure, solo cambian variables/secretos (la llave privada y el JWKS deben salir del mismo par). Un token de local no vale en Azure (llaves distintas) y es lo correcto.
**Validado:** Bicep (`az bicep build/lint`), `shellcheck`, `actionlint`, y el recorrido completo con Docker. **No validado (requiere suscripción real):** `EnableServerless` en Cosmos, que KrakenD/httpx acepten el certificado de `*.internal.<dominio>`, permiso de la suscripción de estudiantes para registrar la app de Entra ID (OIDC), límite por IP tras el ingreso de Azure (se lee `X-Forwarded-For` desde redes privadas), y las consultas reales contra Cosmos.
**Del gateway (limitaciones de KrakenD Community):** 401/403/429/500 generados por el gateway no traen cuerpo; servicio caído → 500 (no 503); sin rutas comodín (se enumeran en `gateway/settings/rutas.json`, `make docs` regenera `docs/rutas.md` y Postman). Falta: llenar `GATEWAY.md` (líder, URL) y la sección 0 de `ApiFlota/docs/integracion.md` con la URL pública.
**Lo que Flota espera del gateway** (ya documentado en `ApiFlota/docs/integracion.md` §13 y MID §2) está implementado: valida token y alcances; agrega `X-Gateway-Secret` por servicio y descarta el del cliente; quita prefijo según tabla; pasa los errores del servicio sin cambios; esperas de 15 s en rutas lentas.

## Pendientes principales (ver PENDIENTES.md de cada repo)
Subir MID y gateway a GitHub (serán públicos; el historial tiene el correo del usuario: conviene el correo noreply de GitHub); reglas de rama y PRs; ejecutar la configuración de Azure y el primer despliegue (ver arriba); probar contra Cosmos real y Viajes y zonas real; confirmar con Viajes y zonas sus rutas/respuesta (`/zonas/verificar`, `permitida`); que adopten las zonas propuestas y validen el punto final con `/localidades/verificar`; completar la sección 0 de `docs/integracion.md` (URL, token, client_ids); entregar docs a los otros equipos; «Aportes de cada integrante» en los READMEs; decidir dónde viven las APIs de terceros (hoy en el CRUD).

## Trampas aprendidas
- Contenedores con `-v` de la carpeta temporal necesitan `--user $(id -u):$(id -g)`.
- `docker run`/`pkill -f` con patrones propios pueden matar la propia shell; el visor de diagramas se sirvió con `python3 -m http.server` local.
- `jq` sin `-c` rompe el cargador SQL de localidades; `ogr2ogr` necesita `-lco PRECISION=NO`.
- Hay un archivo sin seguimiento del usuario, `guiaCD.md`, que no se debe tocar ni commitear.
