.PHONY: up down build migrate lint test

up:
	docker compose up --build -d

down:
	docker compose down

build:
	docker compose build

migrate:
	migrate -path ./database/migrations \
	  -database "postgres://srave_user:$(DB_PASSWORD)@localhost:5432/srave_prod?sslmode=disable" up

migrate-down:
	migrate -path ./database/migrations \
	  -database "postgres://srave_user:$(DB_PASSWORD)@localhost:5432/srave_prod?sslmode=disable" down

seed:
	psql -U srave_user -d srave_prod -f database/seeds/sample_lga_boundaries.sql

lint:
	cd services/core-api && golangci-lint run
	cd services/billing-service && golangci-lint run
	cd services/multilateral-api && golangci-lint run
	cd services/spatial-ingestion && ruff check .

test:
	cd services/core-api && go test ./...
	cd services/billing-service && go test ./...
	cd services/multilateral-api && go test ./...
