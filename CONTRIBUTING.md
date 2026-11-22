# Cómo trabajar en este repositorio

## Git flow con microcommits

| Rama | Para qué |
| --- | --- |
| `main` | Versiones estables (se actualiza con releases) |
| `develop` | Integración: aquí se fusiona todo el trabajo |
| `feature/<tema>` | Un bloque de trabajo; sale de `develop` y vuelve a `develop` |
| `release/x.y.z`, `hotfix/...` | Cuando toque publicar una versión o corregir algo urgente en `main` |

```bash
git checkout develop && git pull
git checkout -b feature/mi-tema
# ... commits pequeños ...
git checkout develop && git merge --no-ff feature/mi-tema && git branch -d feature/mi-tema
```

Si el trabajo se revisa por pull request, el destino es `develop`.

**Microcommits:** cada commit hace una sola cosa y deja el proyecto coherente. Es mejor diez commits de un archivo cada uno que uno gigante. Mensajes en español, en formato [Conventional Commits](https://www.conventionalcommits.org/): `tipo(ámbito): qué cambia`, con tipos `feat`, `fix`, `docs`, `test`, `build`, `refactor`, `style` y `chore`. Ejemplos del historial: `feat(db): agregar cambio de estado atómico con transiciones válidas`, `test: cubrir el clima con simulación, reintentos, caché y degradación`.

## Todo en Docker

No se instala nada en la máquina. Ver los atajos en el [README](README.md#atajos-make).

```bash
make up        # API + MongoDB con recarga en caliente
make test      # pruebas contra un MongoDB real
```

## Dependencias con uv

Las dependencias están en `pyproject.toml` y las versiones exactas en `uv.lock` (ambos se versionan). La imagen instala con `uv sync --frozen`: si el lock no coincide con `pyproject.toml`, el build falla a propósito.

```bash
make add pkg=httpx                    # dependencia de ejecución
make add pkg="--dev pytest-cov"       # dependencia de desarrollo
make lock                             # re-resolver tras editar pyproject.toml
```

## Antes de abrir un pull request

1. `make test` en verde.
2. Si cambió un endpoint, `make openapi`. Si cambió la semilla, `make docs-semilla`. Hay pruebas que fallan si se olvida.
3. Si el cambio afecta a quienes consumen la API, actualizar [docs/integracion.md](docs/integracion.md).
4. Los cambios que rompen el contrato (quitar un campo, cambiar un código de error) se avisan a los grupos consumidores antes de fusionar.
