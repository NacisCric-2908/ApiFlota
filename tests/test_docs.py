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


def test_el_contrato_produce_nombres_limpios_para_los_generadores_de_clientes():
    """Con tildes o guiones bajos los generadores (Java, Python...) inventan nombres como VehculosApi."""
    import re

    contrato = app.openapi()
    assert contrato["info"]["title"].isascii(), "el título da nombre al paquete del cliente Python"
    ids = []
    for ruta, operaciones in contrato["paths"].items():
        for metodo, op in operaciones.items():
            assert re.fullmatch(r"[a-z][A-Za-z0-9]*", op["operationId"]), f"{metodo} {ruta}: {op['operationId']}"
            assert all(t.isascii() and t.isalnum() for t in op["tags"]), f"{metodo} {ruta}: {op['tags']}"
            ids.append(op["operationId"])
    assert len(ids) == len(set(ids)), "operationId repetido"
    assert {t["name"] for t in contrato["tags"]} >= {t for ops in contrato["paths"].values() for o in ops.values() for t in o["tags"]}


# ---------- coherencia entre la documentación, el código y el contrato ----------

def _leer_doc(nombre: str) -> str:
    return (DOCS / nombre).read_text(encoding="utf-8")


def test_cada_endpoint_del_contrato_esta_en_la_guia_de_integracion():
    import re

    guia = _leer_doc("integracion.md")
    for ruta, operaciones in app.openapi()["paths"].items():
        for metodo in operaciones:
            esperado = f"{metodo.upper()} {ruta.replace('{vehiculo_id}', '{id}')}"
            assert re.search(re.escape(esperado), guia), f"falta en integracion.md: {esperado}"


def test_el_catalogo_de_errores_coincide_con_los_codigos_del_codigo_fuente():
    import re

    codigos_en_codigo = set()
    for f in Path("app").rglob("*.py"):
        codigos_en_codigo |= set(re.findall(r'ApiError\(\s*\d+,\s*"([a-z_]+)"', f.read_text(encoding="utf-8")))
        codigos_en_codigo |= set(re.findall(r'cuerpo_error\(\s*"([a-z_]+)"', f.read_text(encoding="utf-8")))
    # Códigos que se generan fuera de ApiError(...): manejadores globales y middleware.
    codigos_en_codigo |= {"solicitud_invalida", "no_encontrado", "metodo_no_permitido", "error_http", "error_interno"}
    guia = _leer_doc("integracion.md")
    catalogo = guia[guia.index("## 8. Catálogo de errores") : guia.index("## 9.")]
    en_catalogo = {c for c in re.findall(r"`([a-z_]+)`", catalogo) if "_" in c}
    assert codigos_en_codigo - en_catalogo == set(), f"códigos sin documentar: {codigos_en_codigo - en_catalogo}"
    assert en_catalogo - codigos_en_codigo == set(), f"documentados pero inexistentes: {en_catalogo - codigos_en_codigo}"


def _ancla(titulo: str) -> str:
    """Ancla de GitHub para un título: minúsculas, sin signos, espacios a guiones."""
    import re

    t = titulo.strip().lower()
    t = re.sub(r"[^\w\s-]", "", t)
    return re.sub(r"\s", "-", t)


def test_los_enlaces_entre_documentos_existen_y_sus_anclas_tambien():
    import re
    from urllib.parse import unquote

    fallos = []
    for md in sorted(DOCS.glob("*.md")):
        for destino in re.findall(r"\]\(([^)\s]+)\)", md.read_text(encoding="utf-8")):
            if destino.startswith(("http://", "https://", "mailto:")):
                continue
            ruta, _, ancla = destino.partition("#")
            objetivo = (md.parent / unquote(ruta)).resolve() if ruta else md.resolve()
            if not objetivo.exists():
                fallos.append(f"{md.name}: no existe {destino}")
            elif ancla and objetivo.suffix == ".md":
                titulos = re.findall(r"^#+\s+(.*)$", objetivo.read_text(encoding="utf-8"), flags=re.M)
                if ancla not in {_ancla(t) for t in titulos}:
                    fallos.append(f"{md.name}: la ancla #{ancla} no existe en {objetivo.name}")
    assert not fallos, "\n".join(fallos)


def test_el_sql_de_las_zonas_esta_al_dia():
    from scripts.generar_docs_semilla import generar_sql

    assert (DOCS / "geo" / "zonas_semilla_postgis.sql").read_text(encoding="utf-8") == generar_sql(), (
        "docs/geo/zonas_semilla_postgis.sql está desactualizado: ejecuta `make docs-semilla`"
    )
