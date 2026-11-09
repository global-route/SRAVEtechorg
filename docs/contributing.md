# Contributing to SRAVE

## Prerequisites

- Go 1.22+
- Python 3.11+
- Flutter 3.22+
- Docker + Docker Compose
- `golang-migrate` CLI
- `golangci-lint`
- `ruff`

## Local Setup

```bash
git clone https://github.com/global-route/SRAVEtechorg.git
cd SRAVEtechorg
cp .env.example .env   # fill in your local values
make up                # starts all services + postgres + redis
make migrate           # runs DB migrations
make seed              # loads sample LGA boundaries
```

Services will be available at:
- core-api: http://localhost:8080
- spatial-ingestion: http://localhost:8001
- billing-service: http://localhost:8002
- multilateral-api: http://localhost:8003

## Workflow

1. Branch from `main`: `git checkout -b feat/your-feature`
2. Make changes, run `make lint` and `make test`
3. Open a pull request against `main`
4. CI must pass before merge

## Licensing

- `/services/core-api`, `/services/billing-service`, `/services/multilateral-api`, `/services/field-agent-app` — MIT License
- `/services/spatial-ingestion` — Apache 2.0
- `/docs` — CC BY 4.0

By contributing you agree your code will be licensed under the applicable license for that directory.
