# Contributing to SRAVE

## Prerequisites

- Python 3.11+
- Flutter 3.22+
- Docker + Docker Compose
- `psql` (PostgreSQL client)
- `ruff` — `pip install ruff`
- `pytest` — `pip install pytest pytest-asyncio httpx`

## Local Setup

```bash
git clone https://github.com/global-route/SRAVEtechorg.git
cd SRAVEtechorg
cp .env.example .env        # fill in your local values
make up                     # starts all services + postgres + redis
make migrate                # runs DB migrations 001–005
make seed                   # loads sample LGA boundaries and default tax rates
```

Services available at:

| Service | URL |
|---|---|
| `api` | http://localhost:8080 |
| `spatial-worker` | http://localhost:8001 |
| `billing-worker` | http://localhost:8002 |
| `multilateral-api` | http://localhost:8003 |
| `voice-service` | http://localhost:8004 |

> Note: Celery workers for `spatial-worker` and `billing-worker` are not yet
> wired into Compose. Until phase 10 lands, queued ingestion and extraction
> tasks will not execute. See [sprint-10.md](sprint-10.md).

## Workflow

1. Branch from `main`: `git checkout -b feat/your-feature`
2. Make changes, run `make lint` and `make test`
3. Open a pull request against `main`
4. All CI jobs must pass before merge (lint + 4 service test jobs)

## CI Jobs

| Job | Triggers on |
|---|---|
| `lint` | every push / PR |
| `test-api` | after lint |
| `test-spatial-worker` | after lint |
| `test-billing-worker` | after lint |
| `test-multilateral-api` | after lint |

Flutter CI (`flutter test`) is planned for phase 10.

## Service Structure

```
services/
├── api/                  ← FastAPI — auth, gap analysis, audit ledger, RBAC
│   ├── routers/          ← one file per route group
│   ├── middleware/       ← auth, RBAC, security headers, request ID
│   ├── models/           ← Pydantic schemas
│   ├── repository/       ← asyncpg DB queries
│   ├── ledger/           ← SHA-256 chain + APScheduler cron
│   └── tests/            ← pytest (auth smoke tests)
├── spatial-worker/       ← FastAPI + Celery — GEE, SAM, YOLOv8, change detection
│   └── tests/            ← pytest (ingest + extraction smoke tests)
├── billing-worker/       ← FastAPI — WhatsApp, Flutterwave, Paystack
│   └── tests/            ← pytest (assess smoke tests)
├── multilateral-api/     ← FastAPI — JSON-LD signed verify, OCDS export
│   └── tests/            ← pytest (verify + OCDS smoke tests)
├── voice-service/        ← FastAPI — MMS TTS, 5 Nigerian languages
└── field-agent-app/      ← Flutter — offline-first, SQLite, TFLite, Mapbox GL
```

## Shared Base

All Python services extend `requirements-base.txt` at the repo root.
Service-specific deps are in each service's own `requirements.txt`.

> Docker build context issue: until phase 10 fixes the Dockerfile and
> `deploy.yml` build context, `docker build` from a service subdirectory
> cannot resolve `../../requirements-base.txt`. Build from repo root or
> run `make up` (Compose handles context correctly via bind mounts).

## Licensing

- `services/api`, `services/billing-worker`, `services/multilateral-api`, `services/voice-service`, `services/field-agent-app` — MIT License
- `services/spatial-worker` — Apache 2.0
- `docs/` — CC BY 4.0
