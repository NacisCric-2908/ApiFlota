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
from app.routers import health, localidades, vehiculos


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    cliente = crear_cliente(settings.mongo_uri)
    app.state.mongo = cliente
    base = cliente[settings.mongo_db]
    app.state.vehiculos = base[NOMBRE_COLECCION]
    app.state.localidades = base[loc_db.NOMBRE_COLECCION]
    # Datos de referencia primero: la validación de «dentro de Bogotá» y la semilla dependen de ellos.
    await loc_db.preparar_indices(app.state.localidades)
    await loc_db.sincronizar(app.state.localidades)
    await preparar_indices(app.state.vehiculos)
    await rellenar_localidades(app.state.vehiculos, app.state.localidades)
    if settings.seed_on_empty:
        await cargar_semilla_si_vacia(app.state.vehiculos, app.state.localidades)
    yield
    await cliente.close()


app = FastAPI(
    title="API Flota - CRUD de Vehículos",
    version="0.1.0",
    description="Inventario de scooters y bicicletas del clúster Rodar (MongoDB, consultas geoespaciales).",
    lifespan=lifespan,
)
registrar_manejadores(app)
instalar_contrato(app)
app.add_middleware(GatewaySecretMiddleware)
app.include_router(health.router)
app.include_router(vehiculos.router)
app.include_router(localidades.router)
