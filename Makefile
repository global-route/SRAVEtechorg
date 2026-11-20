.PHONY: up down build migrate migrate-down seed lint test secrets-dir

up:
	docker compose up --build -d

down:
	docker compose down

build:
	docker compose build

migrate:
	docker compose run --rm srave-api python -m alembic upgrade head

migrate-down:
	docker compose run --rm srave-api python -m alembic downgrade -1

seed:
	psql -U srave_user -d srave_prod -f database/seeds/sample_lga_boundaries.sql
	psql -U srave_user -d srave_prod -f database/seeds/ogun_lga_boundaries.sql

seed-ogun:
	psql -U srave_user -d srave_prod -f database/seeds/ogun_lga_boundaries.sql

seed-delta:
	psql -U srave_user -d srave_prod -f database/seeds/delta_lga_boundaries.sql

lint:
	ruff check services/api services/spatial-worker services/billing-worker \
	             services/multilateral-api services/voice-service
	cd services/dashboard && npm run lint

format:
	ruff format services/

test:
	pytest services/api/tests -v
	pytest services/spatial-worker/tests -v
	pytest services/billing-worker/tests -v
	pytest services/multilateral-api/tests -v

secrets-dir:
	mkdir -p secrets
	@echo "Place gee_key.json and signing.key in ./secrets/"

logs:
	docker compose logs -f --tail=100

ps:
	docker compose ps
