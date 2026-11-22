# Guía de integración: API Flota (CRUD de Vehículos)

Para los grupos que consumen este servicio (MID de Viajes y zonas, MID de Flota, líder del gateway). El contrato formal está en [`openapi.json`](openapi.json) (se puede importar en Postman, Swagger UI o un generador de clientes). Esta guía explica cómo usarlo bien.

## 0. Datos de conexión

> **Pendiente del líder del gateway:** completar esta tabla cuando el gateway esté desplegado. El resto de la guía no cambia.

| Dato | Valor |
| --- | --- |
| URL base del gateway | _por completar_ |
| Pedir un token | `POST {gateway}/token` (OAuth2 *client credentials*; forma exacta que publique el gateway) |
| Prefijo de Flota | `/flota` (el gateway lo quita al reenviar) |
| `client_id` y secreto de su MID | _por completar (los entrega el líder del gateway a cada grupo)_ |
| Alcances de Flota | `vehiculos:leer`, `vehiculos:escribir` |
| Probar sin gateway | Sección 9: levantar Flota local con `make up` |

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
- **Llamada entre el MID de Flota y su propio CRUD (S2S, dentro del mismo entorno, sin pasar por el gateway):** también debe enviar la cabecera `X-Gateway-Secret` con el valor de `GATEWAY_SECRET` de Flota.

## 3. Autenticación y alcances

El gateway emite los tokens (ruta `/token`, credenciales por MID) y valida token y alcances **antes** de reenviar. Este servicio no vuelve a validarlos; solo los declara en el contrato (`security` de cada operación).

| Alcance | Permite |
| --- | --- |
| `vehiculos:leer` | `GET /vehiculos`, `GET /vehiculos/{id}`, `GET /vehiculos/{id}/clima`, `GET /vehiculos/{id}/direccion`, `GET /localidades`, `GET /localidades/verificar`, `GET /localidades/{codigo}` |
| `vehiculos:escribir` | `POST`, `PUT`, `PATCH .../estado` y `DELETE` de vehículos |

`GET /health` es público (sin token ni cabecera).

## 4. Convenciones

- **JSON** con `Content-Type: application/json`. Fechas en ISO 8601 UTC con 6 decimales y `Z` (`2026-11-22T14:20:28.958000Z`).
- **Coordenadas:** GeoJSON, en orden **`[longitud, latitud]`**. En los parámetros de consulta se usan `lat` y `lng` por separado. El error más común es invertirlos; el síntoma es un `400 fuera_de_bogota` con `lat` ≈ -74 en el `detalle`.
- **Cerrado a Bogotá D.C.:** toda ubicación debe caer dentro de una de las 20 localidades. Fuera de Bogotá, el servicio responde `400 fuera_de_bogota`. Guía completa, con cómo conseguir y usar los datos de las localidades: [geoespacial.md](geoespacial.md).
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
  "actualizadoEn": "2026-11-22T14:20:28.958000Z"
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
      "actualizadoEn": "2026-11-22T14:20:28.958000Z", "distanciaMetros": 49.9 }
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
| otro | `error_http` | Cualquier otro error HTTP que no tenga código propio (poco común). El `mensaje` explica | `{}` |
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

Opcional: en vez de escribir las llamadas a mano, se puede generar un cliente a partir de [`openapi.json`](openapi.json). Ambos comandos se ejecutaron y generan sin errores. Los nombres que salen son los del contrato: `operationId` en camelCase (`obtenerVehiculo`, `cambiarEstadoVehiculo`, `verificarLocalidad`...) y una clase por etiqueta (`Vehiculos`, `Localidades`, `Entorno`, `Salud`).

```bash
# Java: genera VehiculosApi, LocalidadesApi, EntornoApi y SaludApi (java.net.http, sin dependencias de Spring)
docker run --rm -v "$PWD:/local" openapitools/openapi-generator-cli generate \
  -i /local/docs/openapi.json -g java --library native -o /local/cliente-flota
#   uso:  new VehiculosApi().cambiarEstadoVehiculo("veh-0003", new CambioEstado().estado(CambioEstado.EstadoEnum.EN_VIAJE));

# Python: crea la carpeta api-flota-crud-de-vehiculos-client
docker run --rm -v "$PWD:/local" -w /local ghcr.io/astral-sh/uv:python3.12-bookworm-slim \
  uvx openapi-python-client generate --path docs/openapi.json
```

El cliente generado **no** agrega el token ni maneja los reintentos o los `409` como lo hace el ejemplo de la sección 11; es una base, no un reemplazo. Se recomienda regenerarlo cuando cambie la versión del contrato (`info.version`).

## 11. Ejemplos de código

El paso de obtener el token lo define el gateway; el ejemplo de Python supone el flujo estándar OAuth2 *client credentials* en `/token` y **no se pudo probar** porque el gateway aún no existe (ajuste los nombres de campos a lo que publique su líder). Todo lo demás de estos ejemplos se ejecutó contra la API real.

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
    r.raise_for_status()  # 404 (no existe) y 5xx (Flota caída) lanzan httpx.HTTPStatusError
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

### Java (Spring Boot 3.2 o superior, `RestClient`)

Un solo archivo, con imports. Cambie el paquete por el suyo. Se compiló con Spring Boot 3.3 y Java 21.

```java
package edu.rodar.viajes.flota;

import com.fasterxml.jackson.annotation.JsonInclude;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClient;

/** Cliente de la API de Flota a través del gateway. */
@Component
public class FlotaClient {

    public record Localidad(String codigo, String nombre) {}

    /** GeoJSON Point: coordinates = [longitud, latitud]. */
    public record Punto(String type, List<Double> coordinates) {
        public static Punto de(double lat, double lng) {
            return new Punto("Point", List.of(lng, lat));
        }
    }

    public record Vehiculo(String id, String tipo, int bateriaPct, String estado,
                           Punto ubicacion, Localidad localidad, Instant actualizadoEn) {}

    @JsonInclude(JsonInclude.Include.NON_NULL)
    record CambioEstado(String estado, Punto ubicacion, Integer bateriaPct) {}

    /** Entrega el token del MID, pedido al gateway. Lo implementa su equipo. */
    public interface TokenProvider {
        String token();
    }

    private final RestClient http;

    public FlotaClient(RestClient.Builder builder, TokenProvider tokens,
                       @Value("${gateway.url}") String gatewayUrl) {
        this.http = builder
            .baseUrl(gatewayUrl + "/flota")
            .requestInterceptor((req, body, ex) -> {
                req.getHeaders().setBearerAuth(tokens.token());
                return ex.execute(req, body);
            })
            .build();
    }

    public Vehiculo obtener(String id) {
        return http.get().uri("/vehiculos/{id}", id).retrieve().body(Vehiculo.class);
    }

    /** @return el vehículo reservado, o vacío si ya no estaba disponible (409). */
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

Configure un *timeout* corto en el `RestClient` (por ejemplo 3 s) y trate `HttpServerErrorException` (5xx) y los timeouts como «Flota no disponible» (`503` en su MID). Un 404 llega como `HttpClientErrorException.NotFound`.

## 12. Simular Flota en las pruebas de ustedes

El enunciado pide pruebas unitarias que simulen a los demás servicios (la compensación al fallar la creación del viaje, Flota caída → 503, etc.). Hay dos formas:

1. **Simular las respuestas** (lo habitual en pruebas unitarias). Respuestas reales de Flota para copiar:

| Situación | Estado HTTP | Cuerpo |
| --- | --- | --- |
| Vehículo disponible | 200 | `{"id":"veh-0003","tipo":"scooter","bateriaPct":64,"estado":"disponible","ubicacion":{"type":"Point","coordinates":[-74.07255,4.7092]},"localidad":{"codigo":"11","nombre":"Suba"},"actualizadoEn":"2026-11-22T14:20:28.958000Z"}` |
| Vehículo con poca batería | 200 | igual, con `"bateriaPct":12` (`veh-0009`) |
| Reserva exitosa | 200 | igual, con `"estado":"en_viaje"` |
| Otro viaje ya lo tomó | 409 | `{"codigo":"transicion_invalida","mensaje":"No se puede pasar de 'en_viaje' a 'en_viaje'.","detalle":{"estadoActual":"en_viaje","estadoSolicitado":"en_viaje"}}` |
| No existe | 404 | `{"codigo":"vehiculo_no_encontrado","mensaje":"No existe el vehículo 'veh-9999'.","detalle":{}}` |
| Punto final fuera de Bogotá | 400 | `{"codigo":"fuera_de_bogota","mensaje":"La ubicación está fuera de Bogotá D.C.","detalle":{"lat":6.24,"lng":-75.58}}` |
| Flota caída | (sin respuesta) | un timeout o `ConnectError`; o un `503` del gateway |

Ejemplo en Python con `httpx.MockTransport` (sin red, sin Flota): verifica que `reservar_vehiculo` devuelve `None` ante un 409 y que un fallo de conexión se propaga. Requiere `pytest` y `pytest-asyncio`, con `asyncio_mode = auto` en su `pytest.ini` (o `@pytest.mark.asyncio` en cada prueba); `reservar_vehiculo` es la función de la sección 11.

```python
import httpx
import pytest

VEHICULO_EN_VIAJE = {"id": "veh-0003", "tipo": "scooter", "bateriaPct": 64, "estado": "en_viaje",
                     "ubicacion": {"type": "Point", "coordinates": [-74.07255, 4.7092]},
                     "localidad": {"codigo": "11", "nombre": "Suba"},
                     "actualizadoEn": "2026-11-22T14:20:28.958000Z"}
CONFLICTO = {"codigo": "transicion_invalida", "mensaje": "No se puede pasar de 'en_viaje' a 'en_viaje'.",
             "detalle": {"estadoActual": "en_viaje", "estadoSolicitado": "en_viaje"}}


def cliente_simulado(respuesta: httpx.Response | Exception) -> httpx.AsyncClient:
    def manejar(request: httpx.Request) -> httpx.Response:
        if isinstance(respuesta, Exception):
            raise respuesta  # p. ej. httpx.ConnectTimeout("Flota no responde")
        return respuesta

    return httpx.AsyncClient(base_url="http://gateway.prueba", transport=httpx.MockTransport(manejar))


async def test_reservar_devuelve_el_vehiculo():
    async with cliente_simulado(httpx.Response(200, json=VEHICULO_EN_VIAJE)) as http:
        assert (await reservar_vehiculo(http, "veh-0003"))["estado"] == "en_viaje"


async def test_reservar_devuelve_none_si_otro_viaje_lo_tomo():
    async with cliente_simulado(httpx.Response(409, json=CONFLICTO)) as http:
        assert await reservar_vehiculo(http, "veh-0003") is None


async def test_si_flota_esta_caida_se_propaga_el_error():
    async with cliente_simulado(httpx.ConnectTimeout("Flota no responde")) as http:
        with pytest.raises(httpx.ConnectTimeout):
            await reservar_vehiculo(http, "veh-0003")
```

Para Java, con `MockRestServiceServer` de Spring y las mismas respuestas (prueba para el `FlotaClient` de la sección 11; se ejecutó y pasa, incluye la comprobación de que la reserva no envía campos nulos y de que la longitud va primero):

```java
package edu.rodar.viajes.flota;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.*;
import static org.springframework.test.web.client.response.MockRestResponseCreators.*;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClient;

class FlotaClientTest {
    // Respuestas reales de la API (copiadas de una ejecución real).
    static final String VEHICULO = "{\"id\":\"veh-0003\",\"tipo\":\"scooter\",\"bateriaPct\":64,\"estado\":\"en_viaje\","
        + "\"ubicacion\":{\"type\":\"Point\",\"coordinates\":[-74.07255,4.7092]},"
        + "\"localidad\":{\"codigo\":\"11\",\"nombre\":\"Suba\"},\"actualizadoEn\":\"2026-11-22T14:20:28.958000Z\"}";
    static final String CONFLICTO = "{\"codigo\":\"transicion_invalida\",\"mensaje\":\"No se puede pasar de 'en_viaje' a 'en_viaje'.\","
        + "\"detalle\":{\"estadoActual\":\"en_viaje\",\"estadoSolicitado\":\"en_viaje\"}}";

    MockRestServiceServer server;
    FlotaClient flota;

    @BeforeEach
    void preparar() {
        RestClient.Builder builder = RestClient.builder();
        server = MockRestServiceServer.bindTo(builder).build();
        flota = new FlotaClient(builder, () -> "token-de-prueba", "http://gateway.prueba");
    }

    @Test
    void obtenerLeeTodosLosCamposIncluidaLaFecha() {
        server.expect(requestTo("http://gateway.prueba/flota/vehiculos/veh-0003"))
            .andExpect(method(org.springframework.http.HttpMethod.GET))
            .andExpect(header("Authorization", "Bearer token-de-prueba"))
            .andRespond(withSuccess(VEHICULO, MediaType.APPLICATION_JSON));
        var v = flota.obtener("veh-0003");
        assertEquals("en_viaje", v.estado());
        assertEquals(64, v.bateriaPct());
        assertEquals("Suba", v.localidad().nombre());
        assertEquals(-74.07255, v.ubicacion().coordinates().get(0));   // longitud primero
        assertEquals("2026-11-22T14:20:28.958Z", v.actualizadoEn().toString());
    }

    @Test
    void reservarNoEnviaCamposNulosYDevuelveElVehiculo() {
        server.expect(requestTo("http://gateway.prueba/flota/vehiculos/veh-0003/estado"))
            .andExpect(method(org.springframework.http.HttpMethod.PATCH))
            .andExpect(content().json("{\"estado\":\"en_viaje\"}", true))   // modo estricto: nada más
            .andRespond(withSuccess(VEHICULO, MediaType.APPLICATION_JSON));
        assertTrue(flota.reservar("veh-0003").isPresent());
    }

    @Test
    void reservarDevuelveVacioSiOtroViajeLoTomo() {
        server.expect(requestTo("http://gateway.prueba/flota/vehiculos/veh-0003/estado"))
            .andRespond(withStatus(HttpStatus.CONFLICT).contentType(MediaType.APPLICATION_JSON).body(CONFLICTO));
        assertTrue(flota.reservar("veh-0003").isEmpty());
    }

    @Test
    void liberarEnviaLongitudPrimeroYRecortaLaBateriaNegativa() {
        server.expect(requestTo("http://gateway.prueba/flota/vehiculos/veh-0003/estado"))
            .andExpect(content().json("{\"estado\":\"disponible\",\"bateriaPct\":0,"
                + "\"ubicacion\":{\"type\":\"Point\",\"coordinates\":[-74.076,4.5981]}}", true))
            .andRespond(withSuccess(VEHICULO, MediaType.APPLICATION_JSON));
        flota.liberar("veh-0003", 4.5981, -74.076, -5);
        server.verify();
    }

    @Test
    void unVehiculoInexistenteLanzaNotFound() {
        server.expect(requestTo("http://gateway.prueba/flota/vehiculos/veh-9999"))
            .andRespond(withStatus(HttpStatus.NOT_FOUND).contentType(MediaType.APPLICATION_JSON)
                .body("{\"codigo\":\"vehiculo_no_encontrado\",\"mensaje\":\"No existe\",\"detalle\":{}}"));
        assertThrows(HttpClientErrorException.NotFound.class, () -> flota.obtener("veh-9999"));
    }
}
```

2. **Usar Flota de verdad, en local.** Para pruebas de integración: `make up` levanta Flota con sus 30 vehículos semilla (sección 9), y `docker compose down -v && make up` los restablece. Las coordenadas y los vehículos concretos están en [semilla.md](semilla.md).

## 13. Para el líder del gateway: qué necesita Flota

| Ruta pública del gateway | Se reenvía a (sin el prefijo `/flota`) | Alcance | Espera máxima recomendada |
| --- | --- | --- | --- |
| `GET /flota/vehiculos`, `GET /flota/vehiculos/{id}` | igual | `vehiculos:leer` | 5 s |
| `GET /flota/localidades`, `/localidades/verificar`, `/localidades/{codigo}` | igual | `vehiculos:leer` | 5 s |
| `GET /flota/vehiculos/{id}/clima` y `/direccion` | igual | `vehiculos:leer` | **15 s** (consultan APIs de terceros; ver abajo) |
| `POST`, `PUT`, `PATCH`, `DELETE /flota/vehiculos...` | igual | `vehiculos:escribir` | 5 s |
| `GET /flota/health` | `GET /health` | ninguno (público) | 2 s |
| `GET /flota/docs`, `/flota/openapi.json` | igual | ninguno (opcional publicarlos) | 5 s |
| `GET /flota/recomendaciones/vehiculo`, `/flota/alertas` | **MID Flota** (otro servicio; aún no implementado) | por definir | 10 s |

Reglas que debe cumplir el gateway **por Flota** (si no, el servicio no funciona o no es seguro):

1. **Agregar `X-Gateway-Secret: <valor>`** a toda petición que reenvíe. El valor es el `GATEWAY_SECRET` configurado en Flota (un secreto por servicio; no es el token de los clientes). Sin esa cabecera, Flota responde `401 gateway_no_autorizado`.
2. **Descartar `X-Gateway-Secret` si el cliente la trae**, y poner la propia. Si no, un cliente podría falsificarla.
3. **Quitar el prefijo `/flota`** al reenviar (Flota publica `/vehiculos`, no `/flota/vehiculos`).
4. **Validar token y alcances antes de reenviar.** Flota no los vuelve a validar; solo los declara en el contrato.
5. **Dejar pasar el estado y el cuerpo de los errores sin cambiarlos** (son JSON con `codigo`, `mensaje` y `detalle`; los consumidores programan contra `codigo`). No los reemplace por páginas HTML.
6. **Si Flota no responde** (conexión rechazada o espera agotada), responder `503` con el mismo formato de error. El paso 10 de la demostración lo exige.
7. **Esperas:** `clima` y `dirección` llaman a un tercero con 3 s por intento y hasta 2 reintentos (3 intentos, con esperas de 0,2 s y 0,4 s entre ellos). En el peor caso el clima tarda ~10 s, y la dirección ~13 s porque además espera hasta 1,1 s por intento para respetar el límite de Nominatim. Con una espera menor a la recomendada, el gateway cortará respuestas que Flota todavía iba a dar. El resto responde en milisegundos.
8. **No exponer Flota por otra vía** que no pase por el gateway: la única protección del servicio es la cabecera del punto 1.
