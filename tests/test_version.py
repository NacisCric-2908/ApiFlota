import tomllib
from pathlib import Path

from app.main import app


def test_la_version_coincide_en_pyproject_la_aplicacion_y_el_contrato():
    """Una sola versión en todos lados: si se sube en un sitio y se olvida otro, esta prueba falla."""
    en_pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    assert app.version == en_pyproject == app.openapi()["info"]["version"]
