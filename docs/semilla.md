# Datos semilla de Flota

> Generado con `make docs-semilla` a partir de `app/db/semilla.py`. No editar a mano.

Al arrancar con la base vacía el servicio carga **30 vehículos** en una cuadrícula de 6 x 5, con 100 m de separación, centrada en **lat 4.711, lng -74.0721** (las coordenadas de ejemplo del enunciado del clúster). Todos quedan a menos de ~350 m del centro.

**Para el grupo de Viajes y zonas:** las zonas que siembren (al menos una prohibida, una de recargo y dos de parqueo) deben cubrir esta misma área. Una búsqueda de 500 m desde el centro encuentra los 30 vehículos.

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
