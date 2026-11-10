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

- The Compose and GitHub Actions Docker builds use each service directory as
  their build context. Service requirements include `../../requirements-base.txt`,
  which is outside that context. As configured, builds that install these
  requirements cannot access the shared file. Build from the repository root
  with each service's Dockerfile, or adjust the requirements/context layout.
- The spatial code defines Celery tasks, but Compose starts `spatial-worker`
  using only its Uvicorn command; it does not start a Celery worker process.
  Add a separate worker process that imports/registers both ingestion and AI
  task modules before relying on queued jobs.
- Reduce image size and build time by separating shared runtime packages from
  service-specific dependencies and pinning transitive versions. Use a
  CPU-appropriate PyTorch wheel where GPUs are unavailable.
- Keep inference isolated from request-serving processes, persist model caches,
  and set memory/CPU/GPU limits based on measured workloads. Avoid preloading
  every voice model when only a subset is needed.
- For production, keep PostgreSQL and Redis on private networks rather than
  publishing their ports, add dependency health checks/readiness handling, and
  configure database backups and persistent storage.
- Coolify is a deployment/operations layer, not an SRAVE runtime dependency.
  The current GitHub Actions workflow builds and pushes service images to GHCR,
  then calls service-specific Coolify webhooks. See
  [Coolify deployment notes](../infrastructure/coolify/deploy-hooks.md).

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
| 9 | `HEAD` | Smoke tests for all 4 Python services, CI workflow fixed (per-service jobs, path fix, no `continue-on-error`), docs updated |

---

## Known Gaps / Next Tasks

| Priority | Area | Detail |
|---|---|---|
| High | Docker build context | `requirements.txt` files reference `../../requirements-base.txt` which is outside each service's build context. Fix: set repo root as build context in `deploy.yml` and `docker-compose.yml`, pass `dockerfile: services/<svc>/Dockerfile`. |
| High | Celery worker process | `docker-compose.yml` starts each service with `uvicorn` only. Celery workers for `spatial-worker` and `billing-worker` need a separate `command:` entry or a second service block. |
| Medium | `billing-worker` async | `routers/assess.py` uses sync `psycopg2`. Should migrate to `asyncpg` for consistency and to avoid blocking the event loop. |
| Medium | Flutter integration tests | `map_screen.dart` and `sync_service.dart` have no widget/unit tests. Add `flutter test` to CI. |
| Low | `voice-service` DB access | `POST /voice/notice/{id}` accepts all fields in the request body but doesn't look up the assessment from DB — the caller (`billing.py`) must pass all fields. Consider a DB lookup inside the voice service for resilience. |
| Low | OpenAPI completeness | `docs/openapi.yaml` only documents 3 of ~20 endpoints. Expand or auto-generate from FastAPI's `/openapi.json`. |
