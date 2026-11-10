# Architecture Overview

SRAVE is composed of five independently deployable Python services behind a single Nginx reverse proxy.

```
                        ┌─────────────────────────────────────┐
                        │           Nginx (TLS 1.3)           │
                        │         api.srave.io :443           │
                        └──────┬──────┬──────┬────────┬───────┘
                               │      │      │        │
                    /spatial   │  /billing   │  /multilateral
                               │      │      │        │
              ┌────────────────┘      │  /api/v1      │
              │                       │      │        │
     ┌────────▼──────────┐  ┌─────────▼────┐ ▼  ┌────▼───────────────┐
     │  spatial-worker   │  │billing-worker│    │  multilateral-api  │
     │ Python / FastAPI  │  │Python/FastAPI│    │  Python / FastAPI  │
     │ GEE + SAM/YOLOv8  │  │WA + Flutterw │    │  SHA-256 signed    │
     └────────┬──────────┘  └──────┬───────┘    └────────────────────┘
              │                    │
              └──────┬─────────────┘
                     │
          ┌──────────▼──────────┐        ┌──────────────────┐
          │      srave-api      │        │  field-agent-app │
          │  Python / FastAPI   │◄───────│  Flutter mobile  │
          │  JWT · RBAC · REST  │        │  offline-first   │
          └──────────┬──────────┘        └──────────────────┘
                     │
          ┌──────────▼──────────┐   ┌──────────────────────┐
          │  PostgreSQL+PostGIS │   │    voice-service     │
          │  Redis (jobs/cache) │   │  Python / FastAPI    │
          └─────────────────────┘   │  MMS TTS · 5 langs   │
                                    └──────────────────────┘
```

## Services

| Service | Language | Port | Responsibility |
|---|---|---|---|
| `api` | Python (FastAPI) | 8080 | Auth, JWT/RBAC, gap analysis, field routing, audit ledger |
| `spatial-worker` | Python (FastAPI + Celery) | 8001 | GEE imagery pull, SAM+YOLOv8 footprint extraction, change detection |
| `billing-worker` | Python (FastAPI + Celery) | 8002 | WhatsApp notices, Flutterwave/Paystack payment links |
| `multilateral-api` | Python (FastAPI) | 8003 | SHA-256 signed compliance metrics for World Bank / UN-Habitat |
| `voice-service` | Python (FastAPI) | 8004 | MMS TTS voice notices in 5 Nigerian languages |
| `field-agent-app` | Flutter | — | Offline-first mobile app for ground-truthing |

## Shared Dependencies

All Python services extend `requirements-base.txt` at the repo root:
- `fastapi`, `uvicorn` — API framework
- `asyncpg` — async PostgreSQL + PostGIS
- `redis[asyncio]` — job queue and caching
- `httpx` — async internal service calls
- `python-jose[cryptography]` — JWT auth
- `pydantic v2` — request/response validation
- `apscheduler` — cron jobs (daily audit snapshot)

## Data Flow

1. `POST /api/v1/spatial/ingest` → `spatial-worker` pulls GEE imagery → SAM+YOLOv8 extracts footprints → writes to `detected_buildings`
2. `srave-api` PostGIS spatial join: `detected_buildings` vs `tax_roll` → revenue gap
3. Field agent verifies buildings via Flutter app → `PATCH /field/buildings/{id}/verify`
4. `billing-worker` sends WhatsApp demand notice + Flutterwave payment link → updates `wa_status`
5. `voice-service` generates MMS TTS audio in owner's language → delivers via WhatsApp voice note
6. `GET /api/v1/multilateral/verify` → SHA-256 chained signed metrics → World Bank / UN-Habitat
