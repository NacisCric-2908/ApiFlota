from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.errors import registrar_manejadores
from app.core.openapi import instalar_contrato
from app.core.security import GatewaySecretMiddleware
from app.db import localidades as loc_db
from app.db.mongo import NOMBRE_COLECCION, crear_cliente, preparar_indices
from app.db.semilla import cargar_semilla_si_vacia
from app.db.vehiculos import rellenar_localidades
from app.externos.contenedor import Externos
from app.routers import entorno, health, localidades, vehiculos


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    cliente = crear_cliente(settings.mongo_uri)
    app.state.mongo = cliente
    base = cliente[settings.mongo_db]
    app.state.vehiculos = base[NOMBRE_COLECCION]
    app.state.localidades = base[loc_db.NOMBRE_COLECCION]
    app.state.externos = Externos(settings)
    # Datos de referencia primero: la validación de «dentro de Bogotá» y la semilla dependen de ellos.
    await loc_db.preparar_indices(app.state.localidades)
    await loc_db.sincronizar(app.state.localidades)
    await preparar_indices(app.state.vehiculos)
    await rellenar_localidades(app.state.vehiculos, app.state.localidades)
    if settings.seed_on_empty:
        await cargar_semilla_si_vacia(app.state.vehiculos, app.state.localidades)
    yield
    await app.state.externos.cerrar()
    await cliente.close()


app = FastAPI(
    title="API Flota - CRUD de Vehiculos",
    version="0.1.0",
    description="Inventario de scooters y bicicletas del clúster Rodar (MongoDB, consultas geoespaciales).",
    lifespan=lifespan,
    # Etiquetas y operationId en ASCII y sin guiones bajos: así los generadores de clientes (Java, Python...)
    # producen nombres limpios (VehiculosApi.obtenerVehiculo) y no VehculosApi.detalleVehiculosVehiculoIdGet.
    openapi_tags=[
        {"name": "Vehiculos", "description": "Inventario de scooters y bicicletas: CRUD, búsqueda por cercanía y cambio de estado atómico."},
        {"name": "Localidades", "description": "Las 20 localidades de Bogotá D.C.: en qué localidad está un punto y su geometría."},
        {"name": "Entorno", "description": "Datos de APIs de terceros sobre la ubicación de un vehículo: clima (Open-Meteo) y dirección (Nominatim)."},
        {"name": "Salud", "description": "Estado del servicio (público, sin token)."},
    ],
)
registrar_manejadores(app)
instalar_contrato(app)
app.add_middleware(GatewaySecretMiddleware)
app.include_router(health.router)
app.include_router(vehiculos.router)
app.include_router(localidades.router)
app.include_router(entorno.router)
