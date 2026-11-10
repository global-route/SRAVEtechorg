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

## Workflow

1. Branch from `main`: `git checkout -b feat/your-feature`
2. Make changes, run `make lint` and `make test`
3. Open a pull request against `main`
4. CI must pass before merge

## Service Structure

```
services/
├── api/                  ← FastAPI — auth, gap analysis, audit ledger, RBAC
│   ├── routers/          ← one file per route group
│   ├── middleware/       ← auth, RBAC, security headers, request ID
│   ├── models/           ← Pydantic schemas
│   ├── repository/       ← asyncpg DB queries
│   ├── ledger/           ← SHA-256 chain + APScheduler cron
│   └── tests/            ← pytest
├── spatial-worker/       ← FastAPI + Celery — GEE, SAM, YOLOv8, change detection
├── billing-worker/       ← FastAPI + Celery — WhatsApp, Flutterwave, Paystack
├── multilateral-api/     ← FastAPI — JSON-LD signed verify, OCDS export
├── voice-service/        ← FastAPI — MMS TTS, 5 Nigerian languages
└── field-agent-app/      ← Flutter — offline-first, SQLite, TFLite, Mapbox
```

## Shared Base

All Python services extend `requirements-base.txt` at the repo root.
Service-specific deps are in each service's own `requirements.txt`.

## Licensing

- `services/api`, `services/billing-worker`, `services/multilateral-api`, `services/voice-service`, `services/field-agent-app` — MIT License
- `services/spatial-worker` — Apache 2.0
- `docs/` — CC BY 4.0
