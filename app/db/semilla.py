"""Datos semilla: 30 vehículos en una cuadrícula de 6 x 5 en Bogotá D.C.

Centro: lat 4.7110, lng -74.0721 (las coordenadas de ejemplo del enunciado del clúster). Todos
quedan a menos de ~350 m del centro, así que una búsqueda de 500 m desde ese punto los encuentra
a todos. Estas coordenadas deben acordarse con el grupo de Viajes y zonas (sus zonas sembradas
deben cubrir esta misma área). La localidad de cada vehículo se calcula al cargar la semilla.
"""

from datetime import datetime, timedelta, timezone

from pymongo.asynchronous.collection import AsyncCollection

from app.db.localidades import buscar_por_punto, referencia

CENTRO_LAT = 4.7110
CENTRO_LNG = -74.0721
PASO = 0.0009  # ~100 m
COLUMNAS = 6
FILAS = 5

# Variedad intencional: hay vehículos bajo 25 % (no recomendables), bajo 15 % y bajo 10 % (alertas).
BATERIAS = [
    92, 78, 64, 55, 41, 88, 30, 73, 12, 95,
    22, 67, 48, 81, 9, 59, 35, 70, 14, 84,
    26, 61, 45, 90, 18, 77, 52, 38, 66, 24,
]  # fmt: skip

SIN_ACTUALIZAR = {7, 20}  # índices con la ubicación vieja (más de 2 h) para probar alertas


def generar_vehiculos(ahora: datetime | None = None) -> list[dict]:
    ahora = ahora or datetime.now(timezone.utc)
    vehiculos = []
    for i in range(COLUMNAS * FILAS):
        col, fila = i % COLUMNAS, i // COLUMNAS
        lng = CENTRO_LNG + (col - (COLUMNAS - 1) / 2) * PASO
        lat = CENTRO_LAT + (fila - (FILAS - 1) / 2) * PASO
        if i % 10 == 9:
            estado = "mantenimiento"
        elif i in (5, 17):
            estado = "en_viaje"
        else:
            estado = "disponible"
        vehiculos.append(
            {
                "_id": f"veh-{i + 1:04d}",
                "tipo": "scooter" if i % 2 == 0 else "bicicleta",
                "bateriaPct": BATERIAS[i],
                "estado": estado,
                "ubicacion": {"type": "Point", "coordinates": [round(lng, 6), round(lat, 6)]},
                "actualizadoEn": ahora - timedelta(hours=3 if i in SIN_ACTUALIZAR else 0, minutes=i),
            }
        )
    return vehiculos


async def cargar_semilla_si_vacia(coleccion: AsyncCollection, localidades: AsyncCollection) -> int:
    """Inserta los vehículos semilla solo si la colección está vacía. Devuelve cuántos insertó."""
    if await coleccion.count_documents({}, limit=1):
        return 0
    vehiculos = generar_vehiculos()
    for v in vehiculos:
        lng, lat = v["ubicacion"]["coordinates"]
        loc = await buscar_por_punto(localidades, lng, lat)
        assert loc is not None, f"{v['_id']} quedó fuera de Bogotá"
        v["localidad"] = referencia(loc)
    resultado = await coleccion.insert_many(vehiculos)
    return len(resultado.inserted_ids)
