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
