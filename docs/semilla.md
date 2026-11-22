# Datos semilla de Flota

> Documento generado automáticamente a partir de los datos semilla de Flota. No editar a mano.

Al arrancar con la base vacía el servicio carga **30 vehículos** en una cuadrícula de 6 x 5, con 100 m de separación, centrada en **lat 4.711, lng -74.0721** (las coordenadas de ejemplo del enunciado del clúster; cae en la localidad de Suba). Todos quedan a menos de ~350 m del centro, así que una búsqueda de 500 m desde ese punto los encuentra a todos.

Se dejó variedad a propósito para poder probar las reglas del MID:

- Batería menor a 25 %: no debe recomendarse. Menor a 15 %: alerta. Menor a 10 %: alerta alta.
- Estados `disponible`, `en_viaje` y `mantenimiento`.
- Dos vehículos con la ubicación sin actualizar hace más de 2 horas (alerta por inactividad).

| id | tipo | batería | estado | lat | lng | localidad | ubicación vieja (>2 h) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `veh-0001` | scooter | 92 % | disponible | 4.709200 | -74.074350 | Suba | no |
| `veh-0002` | bicicleta | 78 % | disponible | 4.709200 | -74.073450 | Suba | no |
| `veh-0003` | scooter | 64 % | disponible | 4.709200 | -74.072550 | Suba | no |
| `veh-0004` | bicicleta | 55 % | disponible | 4.709200 | -74.071650 | Suba | no |
| `veh-0005` | scooter | 41 % | disponible | 4.709200 | -74.070750 | Suba | no |
| `veh-0006` | bicicleta | 88 % | en_viaje | 4.709200 | -74.069850 | Suba | no |
| `veh-0007` | scooter | 30 % | disponible | 4.710100 | -74.074350 | Suba | no |
| `veh-0008` | bicicleta | 73 % | disponible | 4.710100 | -74.073450 | Suba | sí |
| `veh-0009` | scooter | 12 % | disponible | 4.710100 | -74.072550 | Suba | no |
| `veh-0010` | bicicleta | 95 % | mantenimiento | 4.710100 | -74.071650 | Suba | no |
| `veh-0011` | scooter | 22 % | disponible | 4.710100 | -74.070750 | Suba | no |
| `veh-0012` | bicicleta | 67 % | disponible | 4.710100 | -74.069850 | Suba | no |
| `veh-0013` | scooter | 48 % | disponible | 4.711000 | -74.074350 | Suba | no |
| `veh-0014` | bicicleta | 81 % | disponible | 4.711000 | -74.073450 | Suba | no |
| `veh-0015` | scooter | 9 % | disponible | 4.711000 | -74.072550 | Suba | no |
| `veh-0016` | bicicleta | 59 % | disponible | 4.711000 | -74.071650 | Suba | no |
| `veh-0017` | scooter | 35 % | disponible | 4.711000 | -74.070750 | Suba | no |
| `veh-0018` | bicicleta | 70 % | en_viaje | 4.711000 | -74.069850 | Suba | no |
| `veh-0019` | scooter | 14 % | disponible | 4.711900 | -74.074350 | Suba | no |
| `veh-0020` | bicicleta | 84 % | mantenimiento | 4.711900 | -74.073450 | Suba | no |
| `veh-0021` | scooter | 26 % | disponible | 4.711900 | -74.072550 | Suba | sí |
| `veh-0022` | bicicleta | 61 % | disponible | 4.711900 | -74.071650 | Suba | no |
| `veh-0023` | scooter | 45 % | disponible | 4.711900 | -74.070750 | Suba | no |
| `veh-0024` | bicicleta | 90 % | disponible | 4.711900 | -74.069850 | Suba | no |
| `veh-0025` | scooter | 18 % | disponible | 4.712800 | -74.074350 | Suba | no |
| `veh-0026` | bicicleta | 77 % | disponible | 4.712800 | -74.073450 | Suba | no |
| `veh-0027` | scooter | 52 % | disponible | 4.712800 | -74.072550 | Suba | no |
| `veh-0028` | bicicleta | 38 % | disponible | 4.712800 | -74.071650 | Suba | no |
| `veh-0029` | scooter | 66 % | disponible | 4.712800 | -74.070750 | Suba | no |
| `veh-0030` | bicicleta | 24 % | mantenimiento | 4.712800 | -74.069850 | Suba | no |

## Zonas propuestas para Viajes y zonas

El enunciado pide sembrar al menos 4 zonas (1 prohibida, 1 de recargo y 2 de parqueo) que cubran el área de los vehículos y acordarlas con Flota desde el primer día. **Esta es la propuesta de Flota, lista para usar:** si Viajes y zonas la adopta tal cual, las demostraciones funcionan con los datos de ambos grupos. Si prefieren otras coordenadas, avisen: solo hay que mantener estas propiedades.

| Zona | Tipo | Cubre | Vehículos semilla | Cuáles |
| --- | --- | --- | --- | --- |
| Prohibida Centro | prohibida | lat 4.7107 a 4.7113<br>lng -74.0719 a -74.0714 | 1 | `veh-0016` |
| Recargo Oriente | recargo | lat 4.7086 a 4.7134<br>lng -74.071 a -74.0694 | 10 | `veh-0005`, `veh-0006`, `veh-0011`, `veh-0012`, `veh-0017`, `veh-0018`, `veh-0023`, `veh-0024`, `veh-0029`, `veh-0030` |
| Parqueo Occidente | parqueo | lat 4.7086 a 4.7134<br>lng -74.0748 a -74.073 | 10 | `veh-0001`, `veh-0002`, `veh-0007`, `veh-0008`, `veh-0013`, `veh-0014`, `veh-0019`, `veh-0020`, `veh-0025`, `veh-0026` |
| Parqueo Sur | parqueo | lat 4.7086 a 4.71<br>lng -74.073 a -74.071 | 2 | `veh-0003`, `veh-0004` |

Propiedades que se deben conservar si se cambian:

- Las zonas cubren la cuadrícula de la semilla y están dentro de Bogotá (todas, en Suba).
- Las zonas no se traslapan (comparten bordes, no área).
- La zona prohibida contiene al menos un vehículo recomendable (`veh-0016`), para que se vea la regla de descartar por zona, **pero no a todos**: la demostración siempre debe producir al menos una recomendación.
- Queda una franja sin ninguna zona, para probar `permitida: true` fuera de las zonas.
- La zona de recargo es donde se finaliza el viaje en el paso 7 de la demostración.

### Puntos de prueba para `GET /zonas/verificar?lat&lng`

| Caso | lat | lng | `permitida` | Zonas devueltas |
| --- | --- | --- | --- | --- |
| Dentro de la zona prohibida | 4.711 | -74.07165 | `false` | Prohibida Centro |
| En la zona de recargo (paso 7 de la demostración: finalizar el viaje) | 4.711 | -74.0702 | `true` | Recargo Oriente |
| En una zona de parqueo | 4.7092 | -74.072 | `true` | Parqueo Sur |
| Fuera de todas las zonas | 4.7125 | -74.0721 | `true` | (ninguna) |

### Resultado esperado de la recomendación desde el centro

`GET /recomendaciones/vehiculo?lat=4.711&lng=-74.0721` aplicando las reglas del enunciado (500 m, batería de al menos 25 %, sin zona prohibida, `puntaje = distancia − batería × 2`). Con estas zonas se descarta `veh-0016` por estar en la zona prohibida. Los 3 mejores (distancias aproximadas, calculadas sobre la esfera como lo hace MongoDB):

| Puesto | Vehículo | Distancia | Batería | Puntaje |
| --- | --- | --- | --- | --- |
| 1. | `veh-0014` | 150 m | 81 % | -12 |
| 2. | `veh-0022` | 112 m | 61 % | -10 |
| 3. | `veh-0008` | 180 m | 73 % | 34 |

### Las zonas como GeoJSON

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "nombre": "Prohibida Centro",
        "tipo": "prohibida"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              -74.0719,
              4.7107
            ],
            [
              -74.0714,
              4.7107
            ],
            [
              -74.0714,
              4.7113
            ],
            [
              -74.0719,
              4.7113
            ],
            [
              -74.0719,
              4.7107
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "nombre": "Recargo Oriente",
        "tipo": "recargo"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              -74.071,
              4.7086
            ],
            [
              -74.0694,
              4.7086
            ],
            [
              -74.0694,
              4.7134
            ],
            [
              -74.071,
              4.7134
            ],
            [
              -74.071,
              4.7086
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "nombre": "Parqueo Occidente",
        "tipo": "parqueo"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              -74.0748,
              4.7086
            ],
            [
              -74.073,
              4.7086
            ],
            [
              -74.073,
              4.7134
            ],
            [
              -74.0748,
              4.7134
            ],
            [
              -74.0748,
              4.7086
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "nombre": "Parqueo Sur",
        "tipo": "parqueo"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              -74.073,
              4.7086
            ],
            [
              -74.071,
              4.7086
            ],
            [
              -74.071,
              4.71
            ],
            [
              -74.073,
              4.71
            ],
            [
              -74.073,
              4.7086
            ]
          ]
        ]
      }
    }
  ]
}
```

Para cargarlas en PostGIS: [`geo/zonas_semilla_postgis.sql`](geo/zonas_semilla_postgis.sql). Guía completa de uso de los datos geoespaciales: [geoespacial.md](geoespacial.md).
