# Architecture Overview

SRAVE is composed of five independently deployable services behind a single Nginx reverse proxy.

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
     ┌────────▼──────────┐  ┌─────────▼──┐  ▼  ┌─────▼──────────────┐
     │ spatial-ingestion │  │  billing-  │     │  multilateral-api  │
     │  Python / FastAPI │  │  service   │     │    Go / Fiber      │
     │  GEE + SAM/YOLO   │  │  Go/Fiber  │     │  SHA-256 signed    │
     └────────┬──────────┘  └─────┬──────┘     └────────────────────┘
              │                   │
              └──────┬────────────┘
                     │
          ┌──────────▼──────────┐        ┌──────────────────┐
          │     core-api        │        │  field-agent-app │
          │     Go / Fiber      │◄───────│  Flutter mobile  │
          │  JWT · RBAC · REST  │        │  offline-first   │
          └──────────┬──────────┘        └──────────────────┘
                     │
          ┌──────────▼──────────┐
          │  PostgreSQL+PostGIS │
          │  Redis cache        │
          └─────────────────────┘
```

## Services

| Service | Language | Port | Responsibility |
|---|---|---|---|
| core-api | Go (Fiber) | 8080 | Auth, audit gap analysis, field agent routing |
| spatial-ingestion | Python (FastAPI) | 8001 | GEE imagery pull, SAM+YOLOv8 footprint extraction |
| billing-service | Go (Fiber) | 8002 | WhatsApp notices, Flutterwave/Paystack payment links |
| multilateral-api | Go (Fiber) | 8003 | Signed compliance metrics for World Bank / UN-Habitat |
| field-agent-app | Flutter | — | Offline-first mobile app for ground-truthing |

## Data Flow

1. `POST /api/v1/spatial/ingest` → spatial-ingestion pulls imagery → SAM+YOLOv8 extracts footprints → writes to `detected_buildings`
2. core-api spatial join: `detected_buildings` vs `tax_assessments` → revenue gap
3. Field agent verifies unregistered buildings via Flutter app → PATCH verified status
4. billing-service sends WhatsApp demand notice + payment link → updates `wa_status`
5. `GET /api/v1/multilateral/verify` → signed aggregate metrics → World Bank / UN-Habitat
