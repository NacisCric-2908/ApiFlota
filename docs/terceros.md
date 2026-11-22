# APIs de terceros y datos abiertos

Este servicio consume dos APIs externas, gratuitas y **sin llave** (no hay secretos que gestionar), y usa un conjunto de datos abiertos. Los consumen los endpoints `GET /vehiculos/{id}/clima` y `GET /vehiculos/{id}/direccion`.

> Ambas integraciones viven en `app/externos/`. Si el equipo decide que deben estar en el MID de Flota, el paquete se puede mover tal cual: no depende del resto de la aplicación salvo por `Settings`.

## Resumen

| | Clima | Dirección |
| --- | --- | --- |
| **API** | [Open-Meteo](https://open-meteo.com/en/docs) | [Nominatim](https://nominatim.org/release-docs/latest/api/Reverse/) (OpenStreetMap) |
| **Para qué** | Saber si llueve donde está un vehículo (p. ej. recomendar distinto o avisar a operaciones) | Mostrar una dirección legible en vez de coordenadas |
| **Endpoint propio** | `GET /vehiculos/{id}/clima` | `GET /vehiculos/{id}/direccion` |
| **Llamada** | `GET https://api.open-meteo.com/v1/forecast?latitude&longitude&current=...&timezone=UTC` | `GET https://nominatim.openstreetmap.org/reverse?lat&lon&format=jsonv2&zoom=18&accept-language=es` |
| **Autenticación** | Ninguna | Ninguna (exige un `User-Agent` que identifique la aplicación) |
| **Límites** | 600 peticiones por minuto y 10 000 por día en uso gratuito | **1 petición por segundo** como máximo; uso intensivo prohibido |
| **Licencia / atribución** | Datos CC BY 4.0: citar Open-Meteo. Gratuito solo para uso no comercial | Datos © colaboradores de OpenStreetMap, ODbL 1.0: citar OSM |
| **Qué se devuelve** | Temperatura, humedad, precipitación, viento, código del tiempo (WMO), `lluvia` (booleano) | Dirección completa, calle, barrio, código postal |
| **Se envía al tercero** | Solo las coordenadas del vehículo | Solo las coordenadas del vehículo y un `User-Agent` genérico (`ApiFlota-ClusterRodar/0.1`) |

Los términos de uso pueden cambiar: revíselos antes de un uso distinto al académico
([Open-Meteo](https://open-meteo.com/en/terms), [política de Nominatim](https://operations.osmfoundation.org/policies/nominatim/)).

## Reglas de consumo (cómo se cumple cada una)

| Regla | Implementación |
| --- | --- |
| **Tiempo máximo de espera** | 3 s por intento (`EXTERNOS_TIMEOUT_S`) |
| **Reintentos limitados** | Hasta 2 reintentos (3 intentos en total), solo ante fallos transitorios: timeout, corte de red, `429` y `5xx`. Un `4xx` no se reintenta. Espera creciente entre intentos: 0,2 s y 0,4 s (`EXTERNOS_REINTENTOS`, `EXTERNOS_BACKOFF_S`) |
| **Caché** | En memoria. Clima: 10 min, con las coordenadas redondeadas a 2 decimales (~1 km). Dirección: 24 h, redondeadas a 4 decimales (~11 m). Máximo 1000 entradas por caché |
| **Límite de tasa del tercero** | Nominatim: las peticiones salientes (incluidos los reintentos) se espacian a 1,1 s (`NOMINATIM_INTERVALO_S`) |
| **Plan de degradación** | Ver abajo. También está escrito en la descripción de cada endpoint del OpenAPI |
| **Simulación en pruebas** | Las pruebas nunca salen a internet: el cliente HTTP se reemplaza por un simulador (`tests/simulador.py`) que permite forzar éxito, `429`, `5xx`, timeouts, cortes de red y respuestas malformadas |

## Plan de degradación

**Clima (`/vehiculos/{id}/clima`)**

1. Si hay un dato fresco en caché (menos de 10 min) se usa, sin llamar a Open-Meteo. `origen: cache`.
2. Si no, se consulta Open-Meteo. `origen: externo`.
3. Si falla tras los reintentos y hay un dato guardado de hasta 3 h, se sirve como respaldo. `origen: cache_desactualizada`.
4. Si no hay ninguno: `503 servicio_externo_no_disponible` con `detalle: { "servicio": "open-meteo", "motivo": "..." }`.

**Dirección (`/vehiculos/{id}/direccion`)**: igual, pero el respaldo de caché dura 7 días y el paso final **no es un error**:

4. Si no hay nada guardado, se responde `200` con la localidad del vehículo calculada con datos propios: `{ "direccion": "Suba, Bogotá D.C.", "fuente": "Localidades de Bogotá (Datos Abiertos Bogotá)", "origen": "local" }`. Solo da `503` si el vehículo tampoco tiene localidad.

El consumidor debe mirar `origen` si le importa la frescura del dato.

## Datos abiertos: localidades de Bogotá

| | |
| --- | --- |
| **Conjunto** | «Localidad. Bogotá D.C.» |
| **Publicador** | Catastro Distrital / IDECA, a través de Datos Abiertos Bogotá |
| **URL** | <https://datosabiertos.bogota.gov.co/dataset/localidad-bogota-d-c> |
| **Licencia** | Creative Commons Attribution 4.0 (citar la fuente) |
| **Uso** | Delimitar el servicio a Bogotá y asignar la localidad de cada vehículo. No se consulta en vivo: se descarga una vez y se versiona en `app/data/localidades_bogota.geojson`. Ver [geoespacial.md](geoespacial.md) |

## Variables de entorno

| Variable | Por defecto | Qué hace |
| --- | --- | --- |
| `OPEN_METEO_URL` | `https://api.open-meteo.com/v1/forecast` | Endpoint de clima |
| `NOMINATIM_URL` | `https://nominatim.openstreetmap.org/reverse` | Endpoint de geocodificación inversa |
| `EXTERNOS_USER_AGENT` | `ApiFlota-ClusterRodar/0.1` | `User-Agent` enviado a los terceros |
| `EXTERNOS_TIMEOUT_S` | `3` | Tiempo máximo por intento |
| `EXTERNOS_REINTENTOS` | `2` | Reintentos tras el primer intento |
| `EXTERNOS_BACKOFF_S` | `0.2` | Espera inicial entre intentos (se duplica) |
| `NOMINATIM_INTERVALO_S` | `1.1` | Separación mínima entre peticiones a Nominatim |

> Importante en producción: la caché y el control de tasa viven en la memoria de cada proceso. Con varias réplicas, el límite de 1 petición por segundo de Nominatim aplica por réplica; si se escala, conviene una caché compartida (p. ej. Redis).
