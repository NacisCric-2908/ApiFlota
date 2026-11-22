# Atajos. Todo corre dentro de Docker.
.PHONY: up down logs test openapi lock add localidades

up:       ## Levanta MongoDB y la API (desarrollo, con recarga)
	docker compose up -d --build

down:     ## Detiene todo (conserva los datos)
	docker compose down

logs:
	docker compose logs -f api

test:     ## Pruebas contra un MongoDB real
	docker compose --profile test run --rm --build test

openapi:  ## Regenera docs/openapi.json
	docker compose run --rm --no-deps -T api python -c "import json; from app.main import app; print(json.dumps(app.openapi(), ensure_ascii=False, indent=2))" > docs/openapi.json

UV = docker run --rm --user $(shell id -u):$(shell id -g) -e HOME=/tmp -e UV_CACHE_DIR=/tmp/uv-cache \
     -v $(CURDIR):/work -w /work ghcr.io/astral-sh/uv:python3.12-bookworm-slim uv

lock:     ## Re-resuelve y actualiza uv.lock
	$(UV) lock

add:      ## Agrega una dependencia: make add pkg=httpx  (dev: make add pkg="--dev pytest-cov")
	$(UV) add $(pkg)

localidades: ## Regenera app/data/localidades_bogota.geojson desde Datos Abiertos Bogotá
	$(UV) run --no-project --with shapely python scripts/preparar_localidades.py
