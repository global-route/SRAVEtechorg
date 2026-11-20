.PHONY: up down build migrate migrate-down seed lint test secrets-dir backup backup-dir

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

seed-lagos:
	psql -U srave_user -d srave_prod -f database/seeds/lagos_lga_boundaries.sql

seed-rivers:
	psql -U srave_user -d srave_prod -f database/seeds/rivers_lga_boundaries.sql

seed-kano:
	psql -U srave_user -d srave_prod -f database/seeds/kano_lga_boundaries.sql

seed-all-states: seed-ogun seed-delta seed-lagos seed-rivers seed-kano

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

backup:
	docker compose exec postgres-db pg_dump -U srave_user srave_prod | gzip > backups/srave_$(shell date +%Y%m%d_%H%M%S).sql.gz
	@echo "Backup saved to backups/"

backup-dir:
	mkdir -p backups

secrets-dir:
	mkdir -p secrets
	@echo "Place gee_key.json and signing.key in ./secrets/"

logs:
	docker compose logs -f --tail=100

ps:
	docker compose ps
