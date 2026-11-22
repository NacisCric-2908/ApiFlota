# Guía de integración: API Flota (CRUD de Vehículos)

Para los grupos que consumen este servicio (MID de Viajes y zonas, MID de Flota, líder del gateway). El contrato formal está en [`openapi.json`](openapi.json) (se puede importar en Postman, Swagger UI o un generador de clientes). Esta guía explica cómo usarlo bien.

## 1. Quién usa qué

| Consumidor | Qué consume | Alcance |
| --- | --- | --- |
| MID Viajes (grupo Viajes y zonas): integración 4 | `GET /vehiculos/{id}`, `PATCH /vehiculos/{id}/estado` | `vehiculos:leer`, `vehiculos:escribir` |
| MID Flota (este grupo) | `GET /vehiculos` (cercanía), `GET /localidades/verificar` | `vehiculos:leer` |
| Cualquier otro | Ver la referencia de la sección 6 | según endpoint |

## 2. Cómo se llega al servicio

Toda llamada entre grupos pasa por el **API Gateway**. El servicio no es accesible directamente y rechaza con `401` cualquier petición que no traiga la cabecera `X-Gateway-Secret` correcta (la agrega el gateway al reenviar; **los consumidores no la envían ni la conocen**).

- Este servicio publica sus rutas **sin prefijo** (`/vehiculos`). Se asume que el gateway las expone bajo `/flota` y quita el prefijo al reenviar (`GET {gateway}/flota/vehiculos` llega aquí como `GET /vehiculos`). Confirmarlo con el líder del gateway.
- Para probar en local, sin gateway: ver la sección 9.

## 3. Autenticación y alcances

El gateway emite los tokens (ruta `/token`, credenciales por MID) y valida token y alcances **antes** de reenviar. Este servicio no vuelve a validarlos; solo los declara en el contrato (`security` de cada operación).

| Alcance | Permite |
| --- | --- |
| `vehiculos:leer` | `GET /vehiculos`, `GET /vehiculos/{id}`, `GET /vehiculos/{id}/clima`, `GET /vehiculos/{id}/direccion`, `GET /localidades`, `GET /localidades/verificar`, `GET /localidades/{codigo}` |
| `vehiculos:escribir` | `POST`, `PUT`, `PATCH .../estado` y `DELETE` de vehículos |

`GET /health` es público (sin token ni cabecera).

## 4. Convenciones

- **JSON** con `Content-Type: application/json`. Fechas en ISO 8601 UTC (`2026-11-22T14:20:28.958Z`).
- **Coordenadas:** GeoJSON, en orden **`[longitud, latitud]`**. En los parámetros de consulta se usan `lat` y `lng` por separado. El error más común es invertirlos.
- **Cerrado a Bogotá D.C.:** toda ubicación debe caer dentro de una de las 20 localidades. Fuera de Bogotá, el servicio responde `400 fuera_de_bogota`. Ver [geoespacial.md](geoespacial.md).
- **Paginación:** `pagina` (desde 1) y `tamano` (por defecto 20, máximo 100). La respuesta trae `items`, `pagina`, `tamano` y `total`.
- **Errores:** siempre `{ "codigo": "...", "mensaje": "...", "detalle": {} }`. Programe contra `codigo`, no contra `mensaje`. Catálogo en la sección 8. Los datos inválidos responden `400` (no `422`).

## 5. Modelo del vehículo

```json
{
  "id": "veh-0002",
  "tipo": "bicicleta",
  "bateriaPct": 78,
  "estado": "disponible",
  "ubicacion": { "type": "Point", "coordinates": [-74.07345, 4.7092] },
  "localidad": { "codigo": "11", "nombre": "Suba" },
  "actualizadoEn": "2026-11-22T14:20:28.958Z"
}
```

| Campo | Valores / reglas |
| --- | --- |
| `tipo` | `scooter` o `bicicleta` |
| `estado` | `disponible`, `en_viaje`, `mantenimiento` |
| `bateriaPct` | entero de 0 a 100 |
| `localidad` | **la calcula el servicio** a partir de `ubicacion`; no se envía. Se actualiza sola al mover el vehículo |
| `actualizadoEn` | la fija el servicio en cada escritura |
| `distanciaMetros` | solo aparece en búsquedas por cercanía |

**Transiciones de estado válidas** (cualquier otra responde `409 transicion_invalida`, incluido repetir el estado actual):

| Desde \ Hacia | `disponible` | `en_viaje` | `mantenimiento` |
| --- | :---: | :---: | :---: |
| `disponible` | no | sí | sí |
| `en_viaje` | sí | no | sí |
| `mantenimiento` | sí | no | no |

## 6. Referencia de endpoints

### `GET /vehiculos`: listar y buscar

| Parámetro | Descripción |
| --- | --- |
| `tipo`, `estado`, `bateriaMin` | filtros |
| `localidad` | código (`17`) o nombre (`La Candelaria`, `usaquen`); no distingue tildes ni mayúsculas |
| `lat`, `lng`, `radioMetros` | búsqueda por cercanía. `lat` y `lng` van juntas; `radioMetros` vale 500 si se omite (máximo 50 000) y solo se acepta con ellas |
| `pagina`, `tamano` | paginación |

Con cercanía el resultado va **del más cercano al más lejano** e incluye `distanciaMetros` (en metros, calculada sobre la esfera). Sin cercanía va ordenado por `id`.

```bash
curl "$GATEWAY/flota/vehiculos?lat=4.711&lng=-74.0721&radioMetros=120&estado=disponible&tamano=2" \
  -H "Authorization: Bearer $TOKEN"
```

```json
{
  "items": [
    { "id": "veh-0016", "tipo": "bicicleta", "bateriaPct": 59, "estado": "disponible",
      "ubicacion": { "type": "Point", "coordinates": [-74.07165, 4.711] },
      "localidad": { "codigo": "11", "nombre": "Suba" },
      "actualizadoEn": "2026-11-22T14:20:28.958Z", "distanciaMetros": 49.9 }
  ],
  "pagina": 1, "tamano": 2, "total": 5
}
```

Respuestas: `200`, `400` (parámetros inválidos o `busqueda_geo_incompleta`).

### `GET /vehiculos/{id}`: detalle

`200` con el vehículo, o `404 vehiculo_no_encontrado`.

### `POST /vehiculos`: crear

Cuerpo: `tipo`, `bateriaPct`, `estado`, `ubicacion`; `id` es opcional (si se omite se genera `veh-XXXXXXXX`; permitido `A-Z a-z 0-9 _ -`, hasta 40). `201` con `Location: /vehiculos/{id}`. Errores: `400` (datos inválidos o `fuera_de_bogota`), `409 vehiculo_duplicado`.

### `PUT /vehiculos/{id}`: reemplazar

Mismo cuerpo que `POST` (sin `id`; se ignora si viene). `200`, `400`, `404`.

### `PATCH /vehiculos/{id}/estado`: cambiar el estado de forma atómica

Cuerpo: `estado` (obligatorio), `ubicacion` y `bateriaPct` (opcionales). Es **una sola operación condicional** en la base: si dos peticiones compiten por el mismo vehículo, **solo una gana** y la otra recibe `409`. Si se envía `ubicacion`, se recalcula la `localidad` y debe estar en Bogotá.

```bash
curl -X PATCH "$GATEWAY/flota/vehiculos/veh-0002/estado" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"estado":"disponible","bateriaPct":70,"ubicacion":{"type":"Point","coordinates":[-74.0306,4.6948]}}'
```

Respuestas: `200` con el vehículo actualizado; `400`; `404`; `409 transicion_invalida` con `detalle: { "estadoActual": "en_viaje", "estadoSolicitado": "en_viaje" }`.

### `DELETE /vehiculos/{id}`

`204`; `404`; `409 vehiculo_en_viaje` (no se puede eliminar un vehículo en viaje).

### `GET /localidades`

Las 20 localidades con su área y cuántos vehículos hay en cada una, por estado.

```json
[{ "codigo": "01", "nombre": "Usaquén", "areaM2": 65201414,
   "vehiculos": { "total": 1, "disponible": 1, "en_viaje": 0, "mantenimiento": 0 } }, "..."]
```

### `GET /localidades/verificar?lat&lng`

Responde siempre `200`. Dentro de Bogotá: `{ "dentroDeBogota": true, "localidad": { "codigo": "17", "nombre": "La Candelaria" } }`. Fuera: `{ "dentroDeBogota": false, "localidad": null }`. `400` si faltan o son inválidas las coordenadas.

### `GET /localidades/{codigo}`

La localidad como **Feature GeoJSON** (geometría `MultiPolygon`), útil para dibujar mapas o diseñar zonas. `404 localidad_no_encontrada`.

### `GET /vehiculos/{id}/clima` y `GET /vehiculos/{id}/direccion`

Datos de APIs de terceros sobre la ubicación del vehículo. Traen `origen` (`externo`, `cache`, `cache_desactualizada`, `local`) para saber de dónde salió el dato. Detalle, límites y plan de degradación en [terceros.md](terceros.md). `503 servicio_externo_no_disponible` si el tercero cae y no hay respaldo.

## 7. Recetas

### Iniciar un viaje (MID Viajes)

1. `GET /vehiculos/{id}`: `404` si no existe. Si `estado != disponible` o `bateriaPct < 15`, responda `409` al usuario.
2. `PATCH /vehiculos/{id}/estado` con `{"estado":"en_viaje"}`. Si responde `409`, otro viaje lo tomó entre el paso 1 y el 2: trátelo como «vehículo no disponible».
3. Cree el viaje. **Si falla, libere el vehículo** (compensación): `PATCH ... {"estado":"disponible"}`.
4. Si Flota responde `503`/timeout en el paso 1 o 2, no cree el viaje y responda `503`.

> El paso 2 no es idempotente: repetirlo da `409`. Si hay un timeout y no sabe si la reserva ocurrió, haga `GET`: si sigue `disponible` puede reintentar; si está `en_viaje` no hay forma de saber si fue usted, trátelo como no disponible. Se acepta la posibilidad de un vehículo huérfano en `en_viaje`, que un operador puede corregir.

### Finalizar un viaje (MID Viajes)

1. **Antes de guardar el viaje como finalizado**, valide el punto final con `GET /localidades/verificar`. Si `dentroDeBogota` es `false`, Flota rechazará la liberación con `400 fuera_de_bogota`; decida qué hacer *antes* de dejar el viaje en un estado que no puede completarse.
2. Libere el vehículo: `PATCH /vehiculos/{id}/estado` con `{"estado":"disponible","ubicacion":{...},"bateriaPct":N}`.
3. **Batería:** calcule `max(0, bateria - minutos * 0.5)`. Un valor negativo responde `400`.

### Recomendar vehículos (MID Flota)

`GET /vehiculos?lat&lng&radioMetros=500&estado=disponible&bateriaMin=25` ya devuelve los candidatos ordenados por distancia y con `distanciaMetros`; el MID solo aplica el filtro de zonas prohibidas y la puntuación.

## 8. Catálogo de errores

| HTTP | `codigo` | Cuándo | `detalle` |
| --- | --- | --- | --- |
| 400 | `solicitud_invalida` | Cuerpo o parámetros inválidos | `{ "errores": [ { "campo": "bateriaPct", "mensaje": "..." } ] }` |
| 400 | `busqueda_geo_incompleta` | `lat` sin `lng`, o `radioMetros` sin punto | `{}` |
| 400 | `fuera_de_bogota` | La ubicación no está en ninguna localidad | `{ "lat": 6.24, "lng": -75.58 }` |
| 401 | `gateway_no_autorizado` | Falta o es incorrecta la cabecera secreta (no pasó por el gateway) | `{}` |
| 404 | `vehiculo_no_encontrado` | El id no existe | `{}` |
| 404 | `localidad_no_encontrada` | El código no existe | `{}` |
| 404 / 405 | `no_encontrado` / `metodo_no_permitido` | Ruta o método inexistente | `{}` |
| 409 | `transicion_invalida` | Cambio de estado no permitido | `{ "estadoActual", "estadoSolicitado" }` |
| 409 | `vehiculo_en_viaje` | Eliminar un vehículo en viaje | `{}` |
| 409 | `vehiculo_duplicado` | `POST` con un `id` existente | `{}` |
| 503 | `servicio_externo_no_disponible` | Cae un tercero (solo clima y dirección) | `{ "servicio": "open-meteo", "motivo": "http_503" }` |
| 500 | `error_interno` | Falla inesperada | `{}` |

## 9. Probar en local, sin gateway

```bash
git clone <repo> && cd ApiFlota
make up                    # MongoDB + API en http://localhost:8000 (con 30 vehículos semilla)
curl -H "X-Gateway-Secret: cambiar-este-secreto" "http://localhost:8000/vehiculos?tamano=2"
```

Solo en local se envía `X-Gateway-Secret` (el valor de `GATEWAY_SECRET` del `.env`). Swagger UI queda en <http://localhost:8000/docs>. Datos semilla: [semilla.md](semilla.md). Para reiniciarlos: `docker compose down -v && make up`.

## 10. Generar un cliente desde el contrato

```bash
# Java / Spring Boot
docker run --rm -v "$PWD:/local" openapitools/openapi-generator-cli generate \
  -i /local/docs/openapi.json -g java --library native -o /local/cliente-flota

# Python
docker run --rm -v "$PWD:/local" -w /local ghcr.io/astral-sh/uv:python3.12-bookworm-slim \
  uvx openapi-python-client generate --path docs/openapi.json
```

## 11. Ejemplos de código

Los pasos para obtener el token los define el gateway; el siguiente ejemplo supone el flujo estándar OAuth2 *client credentials* en `/token`. Ajuste los nombres de campos a lo que publique su líder.

### Python (httpx)

```python
import httpx

GATEWAY = "https://gateway.ejemplo.edu"  # el que publique el líder del gateway


async def obtener_token(client_id: str, client_secret: str) -> str:
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{GATEWAY}/token", data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "vehiculos:leer vehiculos:escribir",
        })
        r.raise_for_status()
        return r.json()["access_token"]


async def reservar_vehiculo(http: httpx.AsyncClient, vehiculo_id: str) -> dict | None:
    """Devuelve el vehículo reservado, o None si ya no estaba disponible."""
    r = await http.patch(f"/flota/vehiculos/{vehiculo_id}/estado", json={"estado": "en_viaje"})
    if r.status_code == 409:
        return None  # otro viaje lo tomó (o no estaba disponible)
    r.raise_for_status()
    return r.json()


async def liberar_vehiculo(http: httpx.AsyncClient, vehiculo_id: str, lat: float, lng: float, bateria: int):
    r = await http.patch(f"/flota/vehiculos/{vehiculo_id}/estado", json={
        "estado": "disponible",
        "bateriaPct": max(0, bateria),
        "ubicacion": {"type": "Point", "coordinates": [lng, lat]},  # ¡longitud primero!
    })
    r.raise_for_status()


# Uso: timeout corto y cliente reutilizable
# async with httpx.AsyncClient(base_url=GATEWAY, timeout=3.0,
#                              headers={"Authorization": f"Bearer {token}"}) as http:
#     vehiculo = await reservar_vehiculo(http, "veh-0002")
```

### Java (Spring Boot 3.2+, `RestClient`)

```java
public record Localidad(String codigo, String nombre) {}
public record Punto(String type, List<Double> coordinates) {            // [longitud, latitud]
    public static Punto de(double lat, double lng) { return new Punto("Point", List.of(lng, lat)); }
}
public record Vehiculo(String id, String tipo, int bateriaPct, String estado,
                       Punto ubicacion, Localidad localidad, Instant actualizadoEn) {}

@JsonInclude(JsonInclude.Include.NON_NULL)
public record CambioEstado(String estado, Punto ubicacion, Integer bateriaPct) {}

@Component
public class FlotaClient {
    private final RestClient http;

    public FlotaClient(RestClient.Builder builder, TokenProvider tokens,
                       @Value("${gateway.url}") String gatewayUrl) {
        this.http = builder
            .baseUrl(gatewayUrl + "/flota")
            .requestInterceptor((req, body, ex) -> {
                req.getHeaders().setBearerAuth(tokens.token());   // token del MID, pedido al gateway
                return ex.execute(req, body);
            })
            .build();
    }

    public Vehiculo obtener(String id) {
        return http.get().uri("/vehiculos/{id}", id).retrieve().body(Vehiculo.class);
    }

    /** @return el vehículo reservado, o empty si ya no estaba disponible (409). */
    public Optional<Vehiculo> reservar(String id) {
        try {
            return Optional.ofNullable(http.patch().uri("/vehiculos/{id}/estado", id)
                .body(new CambioEstado("en_viaje", null, null))
                .retrieve().body(Vehiculo.class));
        } catch (HttpClientErrorException.Conflict e) {
            return Optional.empty();
        }
    }

    public Vehiculo liberar(String id, double lat, double lng, int bateriaPct) {
        return http.patch().uri("/vehiculos/{id}/estado", id)
            .body(new CambioEstado("disponible", Punto.de(lat, lng), Math.max(0, bateriaPct)))
            .retrieve().body(Vehiculo.class);
    }
}
```

Configure un *timeout* corto en el `RestClient` (por ejemplo 3 s) y trate `HttpServerErrorException` (5xx) y los timeouts como «Flota no disponible» (`503` en su MID).
