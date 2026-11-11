# Contributing to SRAVE

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.11+ | All backend services |
| Flutter | 3.22+ | Field agent mobile app |
| Docker + Docker Compose | 24+ | Local stack |
| Node.js | 20+ | Municipal dashboard |
| `psql` | 15+ | DB seed / migration inspection |
| `ruff` | latest | Python linting — `pip install ruff` |
| `pytest` | latest | Python tests — `pip install pytest pytest-asyncio httpx` |

---

## Local Setup

```bash
git clone https://github.com/global-route/SRAVEtechorg.git
cd SRAVEtechorg
cp .env.example .env          # fill in all values — see .env.example comments
make up                        # builds all images, starts full stack
make migrate                   # runs migrations 001–011 in order
make seed-ogun                 # loads all 20 Ogun State LGA boundaries
```

Services after `make up`:

| Service | URL | Notes |
|---|---|---|
| `srave-api` | http://localhost:8080 | Core REST API |
| `spatial-worker` | http://localhost:8001 | GEE + AI pipeline |
| `billing-worker` | http://localhost:8002 | WhatsApp + payments |
| `multilateral-api` | http://localhost:8003 | Signed compliance metrics |
| `voice-service` | http://localhost:8004 | MMS TTS voice notices |
| `dashboard` | http://localhost:3001 | Municipal web UI |
| Prometheus | http://localhost:9090 | Metrics scraper |
| Grafana | http://localhost:3000 | Dashboards (admin / `GRAFANA_PASSWORD`) |
| Flower | http://localhost:5555 | Celery job monitor |

> PgBouncer sits between all services and Postgres on port 5432 (internal only).
> Postgres and Redis do not publish ports externally.

### Seed an initial admin client

After `make migrate`, create the first admin client directly in the DB:

```bash
# Generate a bcrypt hash for your chosen secret
python3 -c "import bcrypt; print(bcrypt.hashpw(b'your_secret', bcrypt.gensalt()).decode())"

# Insert into the clients table
psql -h localhost -U srave_user -d srave_prod -c \
  "INSERT INTO clients (id, secret_hash, scope) VALUES ('admin_01', '<hash>', 'admin');"
```

Then obtain a JWT:

```bash
curl -s -X POST http://localhost:8080/api/v1/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"client_id":"admin_01","client_secret":"your_secret"}' | jq .
```

---

## Workflow

1. Branch from `main`: `git checkout -b feat/your-feature`
2. Make changes, run `make lint` and `make test`
3. Open a pull request against `main`
4. All CI jobs must pass before merge

---

## CI Jobs

| Job | Triggers on | What it checks |
|---|---|---|
| `lint` | every push / PR | `ruff check` across all 5 Python services |
| `test-api` | after lint | Auth, scope, LGA isolation, token refresh |
| `test-spatial-worker` | after lint | Ingest validation, extraction status |
| `test-billing-worker` | after lint | Assess flow, asyncpg mocks, Paystack fallback |
| `test-multilateral-api` | after lint | Verify endpoint, OCDS export, public key |
| `test-flutter` | after lint | MapScreen widget tests, SyncService unit tests |

Branch protection (task G1) is deferred — enable when ready via GitHub → Settings → Branches.

---

## Service Structure

```
services/
├── api/                    ← FastAPI — auth, gap analysis, audit ledger, RBAC
│   ├── ledger/             ← SHA-256 chain + APScheduler cron (snapshot + reminders)
│   ├── middleware/         ← auth, RBAC, security headers, request ID, structlog config
│   ├── models/             ← Pydantic schemas
│   ├── repository/         ← asyncpg DB queries
│   ├── routers/            ← one file per route group
│   ├── templates/          ← Jinja2 HTML for PDF report
│   └── tests/              ← pytest
├── spatial-worker/         ← FastAPI + Celery — GEE, SAM, YOLOv8, tiled inference
│   └── tests/
├── billing-worker/         ← FastAPI — WhatsApp, Flutterwave, Paystack (with retries)
│   ├── providers/          ← tenacity retry + circuit breaker per provider
│   └── tests/
├── multilateral-api/       ← FastAPI — JSON-LD signed verify, OCDS export
│   └── tests/
├── voice-service/          ← FastAPI — MMS TTS, 5 Nigerian languages, DB lookup
├── dashboard/              ← Next.js 14 — municipal web UI (6 pages)
└── field-agent-app/        ← Flutter — offline-first, SQLite, TFLite, Mapbox GL
    └── test/
```

---

## Database Migrations

Migrations run in order via Alembic (`make migrate`). Never edit an existing migration — add a new one.

| Migration | What it creates / changes |
|---|---|
| 001 | `lg_boundaries`, `detected_buildings` (base schema) |
| 002 | `tax_assessments`, `audit_log` |
| 003 | `tax_roll`, `tax_rates`, default rate seed |
| 004 | `audit_snapshots` immutability trigger, `change_detection_log` |
| 005 | `sync_conflicts`, `owner_language` on `tax_roll` |
| 006 | `property_type`, `scan_date` columns on `detected_buildings` |
| 007 | `audit_snapshots` table (was missing from initial schema) |
| 008 | `photo_url` column on `detected_buildings` |
| 009 | `clients` table (DB-backed auth) |
| 010 | `failed_jobs` table (dead letter queue) |
| 011 | `reminder_sent` added to `wa_status` check constraint |

---

## Shared Base

All Python services install `requirements-base.txt` at the repo root first,
then their own `requirements.txt`. The Dockerfiles handle this — do not add
`-r ../../requirements-base.txt` back to service requirements files.

---

## Licensing

- `services/api`, `services/billing-worker`, `services/multilateral-api`, `services/voice-service`, `services/field-agent-app`, `services/dashboard` — MIT License
- `services/spatial-worker` — Apache 2.0
- `docs/` — CC BY 4.0
