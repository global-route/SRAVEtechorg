# SRAVE — Phase Roadmap (Sprints 11–15)

**Baseline:** Phase 10 complete (`ed5c945`). All services build, deploy, and
test. Docker context fixed, Celery workers wired, billing async, OpenAPI full,
Flutter CI live. Only G1 (branch protection) deferred by choice.

---

## How phases are sequenced

```
Sprint 11 — Production Hardening       ← make what exists safe to run live
Sprint 12 — Auth & Multi-Tenancy       ← replace env-var clients with DB-backed users
Sprint 13 — Pilot Data & Observability ← real LGA data in, metrics out
Sprint 14 — Dashboard & Reporting UI   ← municipal web dashboard
Sprint 15 — Scale & Resilience         ← rate limits, retries, K3s readiness
```

Each sprint is independently deployable. Later sprints depend on earlier ones
only where noted.

---

## Sprint 11 — Production Hardening

**Goal:** The stack is safe to expose to the internet. No secrets in env vars
that should be in a secrets manager, no open DB ports, no missing health
checks, no unbounded queries.

### 11-A — Harden Compose for production

**Problem:** `docker-compose.yml` publishes `postgres-db:5432` and
`redis-cache:6379` on `0.0.0.0`. In any cloud VM deployment these are
reachable from the internet.

**Fix:** Remove `ports:` from `postgres-db` and `redis-cache`. Services
communicate over the Docker bridge network by service name — no external
port needed. Only `srave-api:8080` and Nginx `:443/:80` should be published.

**Files:** `docker-compose.yml`

---

### 11-B — Add DB health checks and readiness to Compose

**Problem:** `srave-api` starts immediately and tries to connect to
`postgres-db` before Postgres is ready. Under a cold start this causes a
connection error and the container exits.

**Fix:** Add `healthcheck:` to `postgres-db` and `redis-cache`, and
`depends_on: condition: service_healthy` to all services that need them.

```yaml
postgres-db:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U srave_user -d srave_prod"]
    interval: 5s
    timeout: 5s
    retries: 10

srave-api:
  depends_on:
    postgres-db:
      condition: service_healthy
    redis-cache:
      condition: service_healthy
```

**Files:** `docker-compose.yml`

---

### 11-C — Add `scan_date` and `property_type` columns to migration 001

**Problem:** `detected_buildings` in migration 001 is missing `scan_date`
and `property_type` columns. These are referenced throughout the codebase
(`postgis_writer.py`, `change_detector.py`, `gap.py`, `assess.py`) but were
never added to the initial schema. They exist implicitly because the app
writes them, but a fresh `make migrate` from scratch will fail or produce
a broken schema.

**Fix:** Add migration `006_detected_buildings_columns.up.sql`:

```sql
ALTER TABLE detected_buildings
  ADD COLUMN IF NOT EXISTS property_type TEXT DEFAULT 'residential_low',
  ADD COLUMN IF NOT EXISTS scan_date     DATE;

CREATE INDEX IF NOT EXISTS idx_detected_buildings_property
  ON detected_buildings (lga_id, property_type);
```

**Files:** `database/migrations/006_detected_buildings_columns.up.sql`,
`database/migrations/006_detected_buildings_columns.down.sql`

---

### 11-D — Add `audit_snapshots` table to migrations

**Problem:** `ledger/chain.py` reads and writes `audit_snapshots` but this
table is never created in any migration. A fresh deploy will fail the first
time the daily cron or `POST /audit/snapshot` runs.

**Fix:** Add migration `007_audit_snapshots.up.sql`:

```sql
CREATE TABLE IF NOT EXISTS audit_snapshots (
    id                 BIGSERIAL PRIMARY KEY,
    lga_id             TEXT NOT NULL,
    snapshot_date      DATE NOT NULL,
    ledger_entry_hash  TEXT NOT NULL,
    previous_hash      TEXT NOT NULL,
    payload_json       JSONB NOT NULL,
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (lga_id, snapshot_date)
);

CREATE INDEX idx_audit_snapshots_lga ON audit_snapshots (lga_id, snapshot_date DESC);
```

**Files:** `database/migrations/007_audit_snapshots.up.sql`,
`database/migrations/007_audit_snapshots.down.sql`

---

### 11-E — Paginate `field/assignments` and add `lga_id` filter

**Problem:** `GET /field/assignments/{agent_id}` returns the 50 most recent
unverified buildings globally — not filtered by the agent's assigned LGA.
In a real deployment with multiple LGAs this returns irrelevant buildings.

**Fix:** Add optional `lga_id` query param and `page`/`limit` pagination.
Update the Flutter `ApiService.getAssignments()` to pass `lga_id`.

**Files:** `services/api/routers/field.py`,
`services/field-agent-app/lib/services/api_service.dart`

---

### 11-F — Add `photo_url` storage to verify flow

**Problem:** `PATCH /field/buildings/{id}/verify` accepts `photo_url` in the
payload but never writes it to the DB. The `detected_buildings` table has no
`photo_url` column. Field agent photos are captured and classified on-device
but the URL is silently dropped.

**Fix:** Add migration `008_building_photo_url.up.sql` adding
`photo_url TEXT` to `detected_buildings`. Update `field.py` to write it.

**Files:** `database/migrations/008_building_photo_url.up.sql`,
`services/api/routers/field.py`

---

### 11-G — Rate limiting per client in Nginx

**Problem:** Nginx has a global `limit_req_zone` at 100r/m per IP. This is
too coarse — a single municipal client making bulk ingest requests will hit
the same limit as a field agent. Webhooks from Flutterwave/Paystack should
be exempt.

**Fix:** Add separate zones per route class:

```nginx
limit_req_zone $binary_remote_addr zone=ingest_limit:10m  rate=10r/m;
limit_req_zone $binary_remote_addr zone=api_limit:10m     rate=200r/m;
limit_req_zone $binary_remote_addr zone=webhook_limit:10m rate=500r/m;
```

Apply `ingest_limit` to `/api/v1/spatial/ingest`, `webhook_limit` to
`/api/v1/billing/webhook/*`, `api_limit` to everything else.

**Files:** `infrastructure/nginx/nginx.conf`

---

### Sprint 11 Summary

| ID | Task | Effort | Blocker? |
|---|---|---|---|
| 11-A | Remove public DB/Redis ports from Compose | XS | Yes — security |
| 11-B | Add health checks + depends_on conditions | XS | Yes — cold start |
| 11-C | Migration 006: `detected_buildings` columns | S | Yes — schema gap |
| 11-D | Migration 007: `audit_snapshots` table | S | Yes — schema gap |
| 11-E | Paginate + filter field assignments | S | No |
| 11-F | Migration 008 + write `photo_url` | S | No |
| 11-G | Per-route Nginx rate limits | XS | No |

---

## Sprint 12 — Auth & Multi-Tenancy

**Goal:** Replace the static env-var client map in `auth.py` with a
DB-backed client registry. Support multiple LGAs as isolated tenants.
Add token refresh. Harden the field agent app with secure token storage.

### 12-A — DB-backed client registry

**Problem:** `routers/auth.py` has `_CLIENTS` built from env vars at module
load time. Adding a new municipal client requires a redeploy. There's no way
to revoke a client without redeploying.

**Fix:**
- Migration `009_clients.up.sql`: `CREATE TABLE clients (id TEXT PRIMARY KEY, secret_hash TEXT, scope TEXT, lga_id TEXT, active BOOLEAN DEFAULT TRUE)`
- Hash secrets with `bcrypt` on insert
- `issue_token()` does a DB lookup + `bcrypt.checkpw()` instead of dict lookup
- Add `POST /api/v1/admin/clients` and `DELETE /api/v1/admin/clients/{id}` (admin scope)

**Files:** `database/migrations/009_clients.up.sql`,
`services/api/routers/auth.py`, `services/api/routers/admin.py`

---

### 12-B — Token refresh endpoint

**Problem:** Tokens expire after 1 hour (`JWT_EXPIRY_SECONDS=3600`). The
Flutter app has no refresh mechanism — when the token expires the agent is
silently locked out until they restart the app.

**Fix:**
- Add `refresh_token` (opaque, stored in Redis with 7-day TTL) to the
  `POST /auth/token` response
- Add `POST /auth/refresh` that validates the refresh token from Redis,
  issues a new access token, rotates the refresh token
- Flutter: store both tokens in `flutter_secure_storage`, call refresh
  before any request that returns 401

**Files:** `services/api/routers/auth.py`,
`services/field-agent-app/lib/services/api_service.dart`

---

### 12-C — LGA-scoped JWT claims

**Problem:** A `municipal` token can read gap analysis for any LGA. There's
no tenant isolation — a municipal client for Ogun State can query Delta State
data.

**Fix:**
- Add `lga_id` claim to JWT payload (from the `clients` table)
- `require_scope()` middleware optionally checks `claims["lga_id"]` matches
  the route's `lga_id` path param
- `admin` scope bypasses the check (cross-LGA access)

**Files:** `services/api/routers/auth.py`,
`services/api/middleware/auth.py`

---

### 12-D — Flutter secure token storage + auto-refresh

**Problem:** The Flutter app uses compile-time `String.fromEnvironment` for
the agent token. This bakes the token into the binary — it can't be rotated
without a new build.

**Fix:**
- Add a login screen (`screens/login_screen.dart`) with client ID + secret
  fields
- On login, call `POST /auth/token`, store access + refresh tokens in
  `flutter_secure_storage`
- `ApiService` reads token from secure storage before each request, calls
  refresh if within 5 minutes of expiry

**Files:** `services/field-agent-app/lib/screens/login_screen.dart`,
`services/field-agent-app/lib/services/api_service.dart`,
`services/field-agent-app/lib/main.dart`

---

### Sprint 12 Summary

| ID | Task | Effort |
|---|---|---|
| 12-A | DB-backed client registry + admin CRUD | M |
| 12-B | Token refresh endpoint + Redis storage | M |
| 12-C | LGA-scoped JWT claims + middleware check | S |
| 12-D | Flutter login screen + secure token storage | M |

---

## Sprint 13 — Pilot Data & Observability

**Goal:** Load real Ogun State LGA boundary data. Wire structured logging and
metrics so the team can see what's happening in production. Add a Celery
Flower dashboard for job monitoring.

### 13-A — Real LGA boundary seed data

**Problem:** `database/seeds/sample_lga_boundaries.sql` has two placeholder
polygons. The gap analysis, field routing, and multilateral reporting all
depend on real LGA geometries.

**Fix:**
- Source official Ogun State LGA boundaries from GADM or NBS shapefiles
- Convert to SQL `INSERT` statements using GeoPandas/ogr2ogr
- Replace `sample_lga_boundaries.sql` with real data for the 20 Ogun LGAs
- Add a `make seed-ogun` Makefile target

**Files:** `database/seeds/ogun_lga_boundaries.sql`, `Makefile`

---

### 13-B — Structured JSON logging across all services

**Problem:** All services use Python's default logging which outputs
unstructured text. In production this makes log aggregation (Loki, CloudWatch,
Datadog) difficult.

**Fix:**
- Add `structlog==24.1.0` to `requirements-base.txt`
- Configure JSON renderer in each service's `main.py` lifespan
- Replace all `print()` and bare `logging.info()` calls with
  `structlog.get_logger().info(event=..., **context)`
- Add `correlation_id` from `X-Request-ID` header to every log entry

**Files:** `requirements-base.txt`, all `services/*/main.py`,
`services/api/middleware/request_id.py`

---

### 13-C — Prometheus metrics endpoint

**Problem:** There's no way to observe request rates, error rates, or Celery
queue depth without SSHing into the server.

**Fix:**
- Add `prometheus-fastapi-instrumentator==6.1.0` to `requirements-base.txt`
- Mount `/metrics` on each FastAPI service (Prometheus scrape endpoint)
- Add a `prometheus` service to `docker-compose.yml` with a scrape config
  targeting all 5 services
- Add a `grafana` service with a pre-built dashboard JSON for SRAVE KPIs:
  request rate, error rate, gap analysis latency, Celery queue depth

**Files:** `requirements-base.txt`, all `services/*/main.py`,
`docker-compose.yml`, `infrastructure/monitoring/prometheus.yml`,
`infrastructure/monitoring/grafana-dashboard.json`

---

### 13-D — Celery Flower for job monitoring

**Problem:** There's no visibility into Celery task state beyond Redis key
inspection. Failed ingestion jobs are invisible unless you query Redis
directly.

**Fix:**
- Add `flower==2.0.1` to `services/spatial-worker/requirements.txt`
- Add a `spatial-flower` service to `docker-compose.yml`:
  ```yaml
  spatial-flower:
    command: celery -A ingestion.tasks.celery_app flower --port=5555
    ports: ["5555:5555"]
  ```
- Protect with basic auth via Nginx

**Files:** `services/spatial-worker/requirements.txt`,
`docker-compose.yml`, `infrastructure/nginx/nginx.conf`

---

### 13-E — Dead letter queue for failed Celery tasks

**Problem:** When `run_ingest` or `run_extraction` fails after max retries,
the task is silently dropped. There's no way to replay it or alert on it.

**Fix:**
- Configure a `dead_letter` queue in Celery settings
- On final retry failure, route task to `dead_letter` queue and write a
  record to a new `failed_jobs` table
- Add `GET /api/v1/admin/failed-jobs` endpoint (admin scope) to list and
  replay failed jobs

**Files:** `services/spatial-worker/ingestion/tasks.py`,
`services/spatial-worker/ai/tasks.py`,
`database/migrations/010_failed_jobs.up.sql`,
`services/api/routers/admin.py`

---

### Sprint 13 Summary

| ID | Task | Effort |
|---|---|---|
| 13-A | Real Ogun LGA boundary seed data | M |
| 13-B | Structured JSON logging (structlog) | S |
| 13-C | Prometheus + Grafana metrics | M |
| 13-D | Celery Flower job dashboard | XS |
| 13-E | Dead letter queue + failed jobs table | M |

---

## Sprint 14 — Municipal Dashboard UI

**Goal:** Give municipal finance officers a web interface to see the revenue
gap, track collections, trigger ingestion, and export reports — without
needing API access.

### 14-A — New `dashboard` service

A lightweight Next.js (or plain React + Vite) SPA served as a static build.
Communicates with `srave-api` via the existing REST API using a `municipal`
scope JWT.

**Pages:**
- `/` — LGA overview: gap analysis card, compliance %, 30-day collections chart
- `/buildings` — paginated table of detected buildings with verified/unverified
  filter, map preview
- `/assessments` — assessment list with wa_status badges, payment link column
- `/ingest` — trigger new satellite scan (bounding box picker on a map),
  poll job status
- `/audit` — snapshot chain viewer, verify-chain button
- `/reports` — download gap analysis as PDF, OCDS export as JSON

**Files:** `services/dashboard/` (new service), `docker-compose.yml`,
`infrastructure/nginx/nginx.conf`

---

### 14-B — PDF report generation

**Problem:** Multilateral institutions and state finance ministries need
printable gap analysis reports, not just JSON.

**Fix:**
- Add `weasyprint==62.0` to a new `services/dashboard/requirements.txt`
- `GET /api/v1/audit/lga/{lga_id}/report.pdf` — renders an HTML template
  with gap analysis, 30-day collections chart (SVG), and the latest audit
  snapshot hash, converts to PDF via WeasyPrint
- Signed with the Ed25519 key from `multilateral-api/signing/signer.py`

**Files:** `services/api/routers/audit.py`,
`services/api/templates/gap_report.html`

---

### 14-C — WhatsApp payment reminder scheduler

**Problem:** Assessments with `wa_status='delivered'` but unpaid after 14
days have no follow-up. There's no reminder mechanism.

**Fix:**
- Add a second APScheduler job in `billing-worker/main.py` that runs daily
  at 09:00
- Queries `tax_assessments WHERE wa_status='delivered' AND assessed_at <
  NOW() - INTERVAL '14 days'`
- Re-sends the WhatsApp notice with a "reminder" flag in the template
- Updates `wa_status='reminder_sent'` (add to enum)
- Add migration `011_wa_status_reminder.up.sql`

**Files:** `services/billing-worker/main.py`,
`database/migrations/011_wa_status_reminder.up.sql`

---

### Sprint 14 Summary

| ID | Task | Effort |
|---|---|---|
| 14-A | Municipal dashboard (Next.js SPA) | L |
| 14-B | PDF report generation (WeasyPrint) | M |
| 14-C | WhatsApp payment reminder scheduler | S |

**Effort key extended:** L = 1–2 days

---

## Sprint 15 — Scale & Resilience

**Goal:** The system handles a full LGA scan (50,000+ buildings) without
falling over. Services recover from transient failures automatically.
K3s manifests are production-complete.

### 15-A — Tile the GeoTIFF before inference

**Problem:** `detector.py` loads the entire 2048×2048 GeoTIFF into memory
as a single numpy array and runs YOLOv8 on it. For a large LGA this will
OOM the worker. YOLOv8 also performs better on 640×640 tiles.

**Fix:**
- In `ai/tasks.py`, before calling `detect_buildings()`, tile the GeoTIFF
  into 640×640 overlapping patches (20px overlap to avoid edge misses)
- Run inference per tile, merge results, deduplicate footprints within 2m
  using the existing PostGIS dedup logic in `postgis_writer.py`
- Add `tile_size` and `overlap_px` as configurable env vars

**Files:** `services/spatial-worker/ai/tasks.py`,
`services/spatial-worker/ai/detector.py`

---

### 15-B — Celery task result TTL and Redis memory cap

**Problem:** Job results are stored in Redis with `setex(..., 86400, ...)` —
24-hour TTL. For a busy LGA with hundreds of daily scans, Redis memory will
grow unboundedly.

**Fix:**
- Add `maxmemory 512mb` and `maxmemory-policy allkeys-lru` to the Redis
  service in `docker-compose.yml` via a `redis.conf` volume mount
- Reduce job TTL to 6 hours for completed jobs, keep 24 hours for failed
  jobs (for replay)

**Files:** `docker-compose.yml`,
`infrastructure/redis/redis.conf` (new),
`services/spatial-worker/ingestion/tasks.py`,
`services/spatial-worker/ai/tasks.py`

---

### 15-C — Retry + circuit breaker for external providers

**Problem:** `flutterwave.py`, `paystack.py`, and `whatsapp.py` use bare
`httpx` with no retry logic. A transient 502 from Flutterwave causes the
entire assess flow to fail and the assessment is left in `pending` state
with no payment link.

**Fix:**
- Add `tenacity==8.3.0` to `requirements-base.txt`
- Wrap each provider call with `@retry(stop=stop_after_attempt(3),
  wait=wait_exponential(min=1, max=10))`
- Add a circuit breaker: after 5 consecutive failures, mark the provider
  as `degraded` in Redis for 60 seconds and skip to the fallback

**Files:** `requirements-base.txt`,
`services/billing-worker/providers/flutterwave.py`,
`services/billing-worker/providers/paystack.py`,
`services/billing-worker/providers/whatsapp.py`

---

### 15-D — Complete K3s manifests

**Problem:** `infrastructure/k3s/manifests/` has `core-api.yaml` and
`services.yaml` but is missing:
- `spatial-celery` and `billing-celery` Deployments (added in phase 10 to
  Compose but not K3s)
- `PersistentVolumeClaim` definitions for model weights and voice models
- `ConfigMap` for Nginx config
- `Ingress` resource for TLS termination
- Resource `requests` and `limits` on all containers

**Fix:** Add the missing manifests and resource constraints based on measured
workloads from sprint 13 Prometheus data.

**Files:** `infrastructure/k3s/manifests/celery-workers.yaml`,
`infrastructure/k3s/manifests/storage.yaml`,
`infrastructure/k3s/manifests/ingress.yaml`,
update all existing manifests with `resources:`

---

### 15-E — Database connection pooling via PgBouncer

**Problem:** Each service creates its own `asyncpg` pool (min 1–2, max 5–10).
With 7 containers (5 services + 2 Celery workers) all connecting to Postgres,
peak connections can reach 70+. PostGIS on a small VM typically supports
~100 connections before degrading.

**Fix:**
- Add a `pgbouncer` service to `docker-compose.yml` in transaction pooling
  mode
- All services connect to `pgbouncer:5432` instead of `postgres-db:5432`
  directly
- Set `pool_mode=transaction`, `max_client_conn=200`, `default_pool_size=20`

**Files:** `docker-compose.yml`,
`infrastructure/pgbouncer/pgbouncer.ini` (new),
update `DB_HOST` default in all service `main.py` files

---

### Sprint 15 Summary

| ID | Task | Effort |
|---|---|---|
| 15-A | GeoTIFF tiling before inference | M |
| 15-B | Redis memory cap + TTL tuning | XS |
| 15-C | Retry + circuit breaker for providers | S |
| 15-D | Complete K3s manifests | M |
| 15-E | PgBouncer connection pooling | S |

---

## Full Roadmap at a Glance

| Sprint | Theme | Key Outcomes |
|---|---|---|
| 10 ✅ | Infrastructure Hardening | Docker builds, Celery workers, async billing, full OpenAPI, Flutter CI |
| 11 | Production Hardening | DB ports closed, schema gaps fixed (migrations 006–008), photo storage, LGA-filtered assignments, per-route rate limits |
| 12 | Auth & Multi-Tenancy | DB clients, token refresh, LGA-scoped JWTs, Flutter login |
| 13 | Pilot Data & Observability | Real Ogun data, structured logs, Prometheus/Grafana, Flower, DLQ |
| 14 | Dashboard & Reporting | Municipal web UI, PDF reports, payment reminders |
| 15 | Scale & Resilience | GeoTIFF tiling, Redis cap, provider retries, K3s complete, PgBouncer |

**Effort key:** XS < 30 min · S < 2 h · M < 4 h · L = 1–2 days
