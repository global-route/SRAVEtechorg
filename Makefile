.PHONY: up down build migrate migrate-down migrate-fresh seed lint test

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

migrate-fresh:
	docker compose run --rm srave-api python -m alembic downgrade base
	docker compose run --rm srave-api python -m alembic upgrade head

seed:
	psql -U srave_user -d srave_prod -f database/seeds/sample_lga_boundaries.sql

lint:
	ruff check services/api
	ruff check services/spatial-worker
	ruff check services/billing-worker
	ruff check services/multilateral-api
	ruff check services/voice-service

format:
	ruff format services/

test:
	pytest services/api/tests -v
	pytest services/spatial-worker/tests -v
	pytest services/billing-worker/tests -v
	pytest services/multilateral-api/tests -v
