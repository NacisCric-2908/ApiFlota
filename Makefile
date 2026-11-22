# Atajos. Todo corre dentro de Docker.
.PHONY: up down logs test openapi

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
