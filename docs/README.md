# Documentación de Flota para los otros equipos

Paquete de entrega del **API CRUD de Flota** (versión 1.0.0). Está pensado para que ningún equipo tenga que preguntar nada: cada documento dice qué contiene, para quién es y qué se verificó.

## ¿Qué debo leer?

| Si usted es… | Lea, en este orden | Lo que necesita de Flota |
| --- | --- | --- |
| **MID o CRUD de Viajes y zonas** (consume Flota: integración 4 del enunciado) | 1. [integracion.md](integracion.md) secciones 0 a 8 y 11 · 2. [geoespacial.md](geoespacial.md) completa · 3. [semilla.md](semilla.md) (zonas propuestas) · 4. [integracion.md](integracion.md) sección 12 (cómo simular Flota en sus pruebas) | `GET /vehiculos/{id}`, `PATCH /vehiculos/{id}/estado`, `GET /localidades/verificar` |
| **Líder del gateway** | [integracion.md](integracion.md) secciones 0, 2, 3 y **13** (qué necesita Flota del gateway) · [openapi.json](openapi.json) | Rutas, alcances, cabecera secreta, tiempos de espera |
| **Cuentas** | Nada es obligatorio: según la matriz de integraciones, Cuentas consulta a Viajes y zonas, no a Flota. Si quiere el formato de error común del clúster: [integracion.md](integracion.md) sección 8 | — |
| **MID de Flota** (mismo grupo, otro repositorio) | [integracion.md](integracion.md) completa · [semilla.md](semilla.md) (incluye el resultado esperado de la recomendación) · [terceros.md](terceros.md) | `GET /vehiculos` con cercanía, `/localidades`, clima y dirección |

## Los documentos

| Documento | Qué contiene | Cómo se verificó |
| --- | --- | --- |
| [integracion.md](integracion.md) | Guía de uso: conexión, autenticación y alcances, modelo, cada endpoint con ejemplos, recetas (iniciar y finalizar un viaje), catálogo de errores, ejemplos en Python y Java, cómo simular Flota, qué necesita el gateway | Cada comportamiento descrito se contrastó con la API real (auditoría automática de 52 comprobaciones). Los ejemplos de Python y Java **se ejecutaron** tal cual están escritos |
| [geoespacial.md](geoespacial.md) | Cómo conseguir y usar los datos de las 20 localidades de Bogotá: de dónde salen, cómo cargarlos en PostGIS, consultas listas, validación de zonas, errores comunes | Las dos vías de carga y todas las consultas se ejecutaron en PostGIS 3.4 real; el código Python se ejecutó |
| [semilla.md](semilla.md) | Los 30 vehículos semilla con coordenadas, **cuatro zonas propuestas para Viajes y zonas**, puntos de prueba con su resultado esperado y el resultado esperado de la recomendación | Generado desde el código (no se desactualiza: un test falla si cambia); las zonas se verificaron en PostGIS |
| [geo/cargar_localidades_postgis.sql](geo/cargar_localidades_postgis.sql) | Script que carga las localidades en PostGIS usando solo `psql` | Ejecutado en PostGIS 3.4 |
| [geo/zonas_semilla_postgis.sql](geo/zonas_semilla_postgis.sql) | Crea la tabla `zonas` con las 4 zonas propuestas y comprueba que están dentro de Bogotá | Ejecutado en PostGIS 3.4 |
| [openapi.json](openapi.json) | Contrato formal (OpenAPI 3.1): endpoints, alcances, errores. Sirve para generar clientes y mocks | Un test falla si no coincide con el código; los generadores de Java y Python se ejecutaron sin errores |
| [terceros.md](terceros.md) | Las APIs externas que usa Flota (Open-Meteo, Nominatim): límites, caché, plan de degradación | Pruebas automáticas con simulación; llamadas reales de comprobación |
| [Proyecto Rodar.drawio](Proyecto%20Rodar.drawio) | Documento conjunto: diagrama de nube (Azure y costos), flujo general, arquitectura y base de datos | Revisado visualmente en draw.io |

## Preguntas que seguramente tendrán

| Pregunta | Respuesta corta | Dónde |
| --- | --- | --- |
| ¿A qué URL llamo y cómo me autentico? | Al gateway, con un token OAuth2 de su MID. **La URL y las credenciales las publica el líder del gateway** (aún por definir) | [integracion.md §0](integracion.md#0-datos-de-conexión) |
| ¿Tengo que enviar `X-Gateway-Secret`? | No. Lo agrega el gateway. Solo se envía al probar Flota en local, o en la llamada entre el MID de Flota y su CRUD | [integracion.md §2](integracion.md#2-cómo-se-llega-al-servicio) |
| ¿Cómo pruebo mi integración? | Flota es un servicio en la nube: no hay que instalar ni clonar nada. Para pruebas unitarias, simulen sus respuestas (sección 12); para integración, usen el ambiente de pruebas con su token (sección 9) | [integracion.md §9 y §12](integracion.md#9-probar-contra-flota) |
| ¿Qué vehículos y coordenadas existen? | 30 vehículos en una cuadrícula de 6 × 5 alrededor de lat 4.7110, lng -74.0721 (localidad de Suba) | [semilla.md](semilla.md) |
| ¿Qué zonas debo sembrar? | Flota propone 4 (1 prohibida, 1 de recargo, 2 de parqueo) con coordenadas, SQL y puntos de prueba | [semilla.md](semilla.md#zonas-propuestas-para-viajes-y-zonas) |
| ¿Latitud o longitud primero? | **Longitud primero** en GeoJSON, PostGIS y MongoDB (`[lng, lat]`). Los parámetros de consulta son `lat` y `lng` por separado | [geoespacial.md §8](geoespacial.md#8-errores-comunes) |
| ¿De dónde saco los datos de las localidades y cómo los uso? | Flota las sirve ya preparadas (`GET /localidades/{codigo}`), o se bajan del Distrito (datos abiertos). Si solo necesita saber en qué localidad está un punto, ni las cargue: llame a `/localidades/verificar` | [geoespacial.md](geoespacial.md) |
| ¿Por qué Flota rechaza un punto que sí está en Bogotá? | Casi siempre las coordenadas están invertidas: mire `detalle.lat` en el error; si es ≈ -74, están al revés | [geoespacial.md §8](geoespacial.md#8-errores-comunes) |
| ¿Se pueden poner vehículos fuera de Bogotá? | No: Flota está acotado a Bogotá D.C. (decisión de diseño del grupo). Responde `400 fuera_de_bogota` | [geoespacial.md](geoespacial.md) |
| ¿Qué pasa si dos viajes piden el mismo vehículo a la vez? | Solo uno gana; el otro recibe `409`. La reserva es una operación atómica | [integracion.md §6](integracion.md#6-referencia-de-endpoints) |
| ¿Y si reservé el vehículo y luego falla la creación del viaje? | Hay que liberarlo (`PATCH ... estado: disponible`). Es la compensación que pide el enunciado | [integracion.md §7](integracion.md#7-recetas) |
| ¿Y si el viaje termina fuera de Bogotá? | Flota rechazaría liberar el vehículo (`400`). **Se recomienda validar el punto con `/localidades/verificar` antes de guardar el viaje como finalizado** | [integracion.md §7](integracion.md#7-recetas) |
| ¿Qué hago si Flota está caída? | No cree el viaje y responda `503` (V-HU6 del enunciado) | [integracion.md §7](integracion.md#7-recetas) |
| ¿Cómo sé si el contrato cambió? | Mire `info.version` en `openapi.json` (sigue versionado semántico). Un cambio incompatible sube la versión mayor y se avisa antes | Abajo |

## Versiones del contrato

- La API usa **versionado semántico**. La versión está en `info.version` de [openapi.json](openapi.json).
- Agregar endpoints o campos opcionales sube la versión menor y **no rompe** a nadie.
- Quitar o renombrar un campo, cambiar un código de error o una regla sube la versión **mayor** y se avisa a los grupos consumidores antes de publicarla.

## Una cosa que sigue abierta

**Datos de conexión y ambiente de pruebas:** la URL del gateway, el token, los `client_id` y la URL del ambiente de pruebas (sección 0 de la guía) los completa el líder del gateway cuando esté desplegado.
