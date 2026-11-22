"""Guardas para que la documentación generada no se desactualice."""

import json
from pathlib import Path

from app.db.localidades import RUTA_GEOJSON
from app.db.semilla import cargar_semilla_si_vacia
from app.main import app
from scripts.generar_docs_semilla import generar, localidad_de

DOCS = Path("docs")


def test_el_contrato_openapi_esta_al_dia():
    publicado = json.loads((DOCS / "openapi.json").read_text(encoding="utf-8"))
    actual = json.loads(json.dumps(app.openapi()))
    assert publicado == actual, "docs/openapi.json está desactualizado: ejecuta `make openapi`"


def test_el_documento_de_la_semilla_esta_al_dia():
    assert (DOCS / "semilla.md").read_text(encoding="utf-8") == generar(), (
        "docs/semilla.md está desactualizado: ejecuta `make docs-semilla`"
    )


async def test_la_localidad_calculada_en_python_coincide_con_la_de_mongodb(cliente, coleccion, localidades):
    """El documento de la semilla usa punto-en-polígono en Python; el servicio usa $geoIntersects."""
    features = json.loads(RUTA_GEOJSON.read_text(encoding="utf-8"))["features"]
    await cargar_semilla_si_vacia(coleccion, localidades)
    async for v in coleccion.find():
        lng, lat = v["ubicacion"]["coordinates"]
        assert v["localidad"]["nombre"] == localidad_de(lng, lat, features)["nombre"], v["_id"]
