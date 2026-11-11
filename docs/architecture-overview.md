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
| `spatial-worker` | Python (FastAPI; Celery task definitions) | 8001 | GEE imagery pull, YOLOv8+SAM footprint extraction |
| `billing-worker` | Python (FastAPI) | 8002 | WhatsApp notices, Flutterwave/Paystack payment links |
| `multilateral-api` | Python (FastAPI) | 8003 | SHA-256 signed compliance metrics for World Bank / UN-Habitat |
| `voice-service` | Python (FastAPI) | 8004 | MMS TTS voice notices in 5 Nigerian languages |
| `field-agent-app` | Flutter | — | Offline-first mobile app for ground-truthing |

## Dependency roles

The Python services reference `requirements-base.txt` from their local
`requirements.txt` files, then add service-specific packages:

| Dependencies | Capability |
|---|---|
| FastAPI, Uvicorn, Pydantic | HTTP APIs, request validation, and serving |
| asyncpg, Redis, httpx | PostgreSQL/PostGIS access, cache/job state, and service/provider calls |
| python-jose, cryptography | JWT handling and cryptographic signing |
| Celery | Background task definitions and queueing (spatial service) |
| Earth Engine API, Rasterio, GeoPandas, Shapely | Imagery access and raster/vector geospatial processing |
| PyTorch, Ultralytics, Segment Anything | Declared inference stack for building detection |
| Transformers, SoundFile, pydub, FFmpeg | Text-to-speech inference and audio conversion |
| Flutter packages | Offline SQLite storage, networking, maps, camera/GPS, secure storage, and TFLite |

These are capabilities the declared packages support, not guarantees that each
feature is production-ready. In particular, model checkpoint files are not
stored in the repository; the spatial and voice services expect model files or
caches on `/models`.

## Deployment status and optimization

All known deployment blockers have been resolved as of phase 15:

- Docker build context fixed — all Dockerfiles copy `requirements-base.txt` from repo root
- Celery workers (`spatial-celery`, `billing-celery`) are defined in Compose and K3s
- Postgres and Redis do not publish external ports
- All services connect via PgBouncer (transaction pooling, max 200 client connections)
- Redis has a 512MB memory cap with LRU eviction
- Health checks and `depends_on: condition: service_healthy` on all services
- Resource `requests` and `limits` on all K3s Deployments

See [Coolify deployment notes](../infrastructure/coolify/deploy-hooks.md) for
the current deployment workflow and [docs/runbook.md](runbook.md) for
operational procedures.

## Data Flow

1. `POST /api/v1/spatial/ingest` → `spatial-worker` pulls GEE imagery → SAM+YOLOv8 extracts footprints → writes to `detected_buildings`
2. `srave-api` PostGIS spatial join: `detected_buildings` vs `tax_roll` → revenue gap
3. Field agent verifies buildings via Flutter app → `PATCH /field/buildings/{id}/verify`
4. `billing-worker` sends WhatsApp demand notice + Flutterwave payment link → updates `wa_status`
5. `voice-service` generates MMS TTS audio in owner's language → delivers via WhatsApp voice note
6. `GET /api/v1/multilateral/verify` → SHA-256 chained signed metrics → World Bank / UN-Habitat

---

## Completed Phases

| Phase | Commit | What shipped |
|---|---|---|
| 0 | `06699c7` | DB/Redis lifespan wiring, health checks, auth tests, migrations 003–004, K3s manifests, Nginx |
| 1 | `ce68e2a` | GEE client, YOLOv8+SAM detector, Celery ingest/extraction tasks, PostGIS writer, change detector |
| 2–6 | `23df9c6` | Gap engine, billing DB+providers (Paystack, Flutterwave, WhatsApp), daily snapshot cron, Flutter SQLite+sync+classifier, multilateral metrics+OCDS, voice MMS TTS |
| 7 | `352d612` | Security headers middleware, request ID middleware, migration 005 (sync_conflicts), contributing.md |
| 8 | `36eb893` | `ai/router.py` extraction endpoint (was stub), MapScreen Mapbox GL + verify flow, `api_service.dart` response parsing fix |
| 9 | `4ca4ccc` | Smoke tests for all 4 Python services, CI workflow fixed (per-service jobs, path fix, no `continue-on-error`), docs updated |
| 10 | `ed5c945` | Docker build context fixed (all 5 services), Celery workers wired, billing asyncpg migration, full OpenAPI spec (22 endpoints), Flutter CI + widget/unit tests, voice-service DB lookup |
| 11 | `e18c7e7` | DB/Redis ports closed, health checks, migrations 006–008 (schema gaps + photo_url), LGA-filtered assignments, per-route Nginx rate limits |
| 12 | `a5c99be` | DB-backed clients + bcrypt, token refresh via Redis, LGA-scoped JWT middleware, Flutter login screen + auto-refresh |
| 13 | `9ee1ca1` | All 20 Ogun LGA boundaries, structlog JSON logging, Prometheus + Grafana, Celery Flower, dead letter queue + failed_jobs |
| 14 | `fd33430` | Next.js municipal dashboard (6 pages), WeasyPrint PDF report, payment reminder scheduler, migration 011 |
| 15 | `6b4abf6` | GeoTIFF tiling, Redis memory cap, provider retries + circuit breakers, complete K3s manifests, PgBouncer |

---

## Documentation

| Document | What it covers |
|---|---|
| [contributing.md](contributing.md) | Local setup, workflow, CI jobs, migration table |
| [runbook.md](runbook.md) | Deploy, rollback, DB backup, model loading, incident response |
| [data-model.md](data-model.md) | Full schema reference — all 11 migrations, indexes, key queries |
| [security.md](security.md) | Auth model, scopes, LGA isolation, secrets, TLS, NDPA/GDPR |
| [integrations.md](integrations.md) | GEE, WhatsApp, Flutterwave, Paystack, Mapbox, MMS-TTS setup |
| [openapi.yaml](openapi.yaml) | Full OpenAPI 3.0 spec — all 22 endpoints |
| [roadmap.md](roadmap.md) | Sprints 11–15 task breakdown (all complete) |
