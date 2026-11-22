# Cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). El proyecto usa [versionado semántico](https://semver.org/lang/es/): un cambio incompatible del contrato sube la versión mayor y se avisa a los grupos consumidores antes de publicarlo.

## [1.0.0] - 2026-11-22

Primera versión estable del **API CRUD de Flota** (clúster Rodar).

### Agregado

- **CRUD de vehículos** (`/vehiculos`): listar, detalle, crear, reemplazar, cambiar estado y eliminar, con validación de datos (batería de 0 a 100, tipo, estado, coordenadas) y formato de error común `{codigo, mensaje, detalle}`; los datos inválidos responden 400.
- **Búsqueda por cercanía** con índice geoespacial 2dsphere (`lat`, `lng`, `radioMetros`): del más cercano al más lejano, con `distanciaMetros`. Filtros por `tipo`, `estado`, `bateriaMin` y `localidad`, y paginación.
- **Cambio de estado atómico** (`PATCH /vehiculos/{id}/estado`): una sola operación condicional en MongoDB, de modo que si dos viajes piden el mismo vehículo solo uno gana (el otro recibe 409). Transiciones de estado válidas documentadas.
- **Cerrado a Bogotá D.C.:** las 20 localidades oficiales (Datos Abiertos Bogotá, CC BY 4.0, sin huecos ni traslapes). Toda ubicación se valida (`400 fuera_de_bogota`) y cada vehículo guarda su localidad. Endpoints `GET /localidades`, `/localidades/verificar` y `/localidades/{codigo}`.
- **APIs de terceros gratuitas** sobre la ubicación de un vehículo: clima (Open-Meteo) y dirección (Nominatim/OpenStreetMap), con tiempo máximo de espera, reintentos limitados, caché, límite de 1 petición por segundo para Nominatim y plan de degradación.
- **30 vehículos semilla** que se cargan al arrancar con la base vacía.
- **Seguridad:** rechaza con 401 toda petición que no traiga la cabecera `X-Gateway-Secret` del gateway.
- **Contrato OpenAPI 3.1** (`docs/openapi.json`) con alcances y errores declarados, y `operationId` claros para generar clientes.
- **Docker y Docker Compose** para todo (API, MongoDB y pruebas); dependencias con **uv**.
- **150 pruebas** contra un MongoDB real (sin salir a internet), incluidas las que impiden que la documentación y el contrato se desactualicen.
- **Documentación para los otros grupos** (`docs/`): guía de integración con ejemplos en Python y Java ejecutados, guía geoespacial con recetas verificadas en PostGIS, datos semilla con **zonas propuestas para Viajes y zonas**, fichas de los terceros y diagramas del proyecto (nube en Azure con costos, flujo general, arquitectura y base de datos).

### Limitaciones conocidas

- **No se ha probado contra Azure Cosmos DB real.** La documentación de Microsoft indica que soporta todo lo que usa el servicio (`$geoNear`, `$geoIntersects`, `$facet`, 2dsphere, `findAndModify`), pero las pruebas automáticas corren contra MongoDB.
- La validación de token y alcances la hace el **gateway**; el servicio solo confía en la cabecera `X-Gateway-Secret`.
- `/docs` y `/openapi.json` son públicos (sin la cabecera). Decidir si se exponen en producción.
- La caché y el control de tasa de las APIs de terceros viven en la memoria de cada réplica.
- `/health` solo indica que el proceso está vivo; no consulta MongoDB.
- `docker-compose.yml` trae un `GATEWAY_SECRET` de desarrollo por defecto: debe cambiarse en cada entorno.

