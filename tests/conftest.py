"""Las pruebas usan un MongoDB real (servicio `mongo` de docker compose) y la base `flota_test`."""

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import app

SECRETO = "test-secret"


@pytest_asyncio.fixture
async def cliente():
    # Protección: nunca vaciar una base que no sea de pruebas.
    assert get_settings().mongo_db.endswith("_test"), "MONGO_DB debe terminar en _test"
    async with LifespanManager(app) as manager:
        await app.state.vehiculos.delete_many({})
        transporte = ASGITransport(app=manager.app)
        async with AsyncClient(
            transport=transporte, base_url="http://test", headers={"X-Gateway-Secret": SECRETO}
        ) as c:
            yield c


@pytest.fixture
def coleccion(cliente):
    return app.state.vehiculos


@pytest.fixture
def localidades(cliente):
    return app.state.localidades


@pytest.fixture
def payload():
    """Fábrica de cuerpos válidos para crear vehículos; acepta sobreescrituras."""

    def _crear(**cambios):
        base = {
            "tipo": "scooter",
            "bateriaPct": 80,
            "estado": "disponible",
            "ubicacion": {"type": "Point", "coordinates": [-74.0721, 4.7110]},
        }
        return {**base, **cambios}

    return _crear


@pytest_asyncio.fixture
async def crear_vehiculo(cliente, payload):
    async def _crear(**cambios):
        r = await cliente.post("/vehiculos", json=payload(**cambios))
        assert r.status_code == 201, r.text
        return r.json()

    return _crear
