# Sprint 10 — Infrastructure Hardening & Deploy Readiness

**Goal:** Make every service buildable, deployable, and testable end-to-end.
After this sprint, `make up` produces a fully functional local stack, CI covers
all services including Flutter, and a production deploy via Coolify works
without manual intervention.

**Branch:** `feat/phase-10-infra-hardening`
**Depends on:** Phase 9 merged (`4ca4ccc`)

---

## Track A — Docker Build Context (blocker for deploy)

Every service `requirements.txt` references `../../requirements-base.txt`.
Docker cannot resolve paths outside the build context, so `docker build
services/api` fails. CI uses `pip install -r ../../requirements-base.txt`
with `working-directory` set, which works in Actions but not in a standalone
`docker build`.

### A1 — Fix Dockerfiles to copy shared base from repo root

**Files:** `services/*/Dockerfile` (all 5)

Each Dockerfile currently does:
```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
```

Change to:
```dockerfile
COPY requirements-base.txt .
COPY services/<svc>/requirements.txt ./requirements.txt
RUN pip install -r requirements-base.txt -r requirements.txt
```

And update each `requirements.txt` to remove the `../../requirements-base.txt`
line (it will be installed separately).

**Acceptance:** `docker build -f services/api/Dockerfile .` succeeds from repo
root with no path errors.

---

### A2 — Fix `deploy.yml` build context

**File:** `.github/workflows/deploy.yml`

Change each matrix build step from:
```yaml
context: services/${{ matrix.service }}
```
to:
```yaml
context: .
file: services/${{ matrix.service }}/Dockerfile
```

**Acceptance:** GitHub Actions deploy job builds and pushes all 5 images
without `COPY` path errors.

---

### A3 — Fix `docker-compose.yml` build context

**File:** `docker-compose.yml`

Change each service `build:` from:
```yaml
build: ./services/api
```
to:
```yaml
build:
  context: .
  dockerfile: services/api/Dockerfile
```

Apply to all 5 services.

**Acceptance:** `make build` completes cleanly.

---

## Track B — Celery Workers (blocker for spatial pipeline)

`docker-compose.yml` starts `spatial-worker` and `billing-worker` with
`uvicorn` only. Queued Celery tasks never execute because no worker process
is consuming from Redis.

### B1 — Add `spatial-celery` worker to Compose

**File:** `docker-compose.yml`

Add after the `spatial-worker` service:
```yaml
spatial-celery:
  build:
    context: .
    dockerfile: services/spatial-worker/Dockerfile
  command: celery -A ingestion.tasks.celery_app worker --loglevel=info -Q celery --concurrency=2
  env_file: .env
  depends_on: [postgres-db, redis-cache]
  volumes: [srave-model-weights:/models]
  restart: unless-stopped
```

**Acceptance:** `docker compose up` starts a `spatial-celery` container;
`celery inspect active` shows it connected to Redis.

---

### B2 — Add `billing-celery` worker to Compose

**File:** `docker-compose.yml`

`billing-worker` does not currently define Celery tasks, but the
`requirements.txt` includes `celery==5.4.0` and the assess flow is
synchronous. This task adds the worker container as a placeholder so the
pattern is consistent and ready for async assess jobs in a future phase.

```yaml
billing-celery:
  build:
    context: .
    dockerfile: services/billing-worker/Dockerfile
  command: celery -A routers.assess worker --loglevel=info --concurrency=2
  env_file: .env
  depends_on: [postgres-db, redis-cache]
  restart: unless-stopped
```

**Acceptance:** Container starts without error. No tasks required to run yet.

---

### B3 — Update `deploy-hooks.md` to mark Celery gap resolved

**File:** `infrastructure/coolify/deploy-hooks.md`

Remove the "Compose stack does not currently start a Celery worker" warning
and replace with a note that `spatial-celery` and `billing-celery` are now
defined and require their own Coolify resources or a combined deployment
with the parent service.

---

## Track C — `billing-worker` Async Migration

**File:** `services/billing-worker/routers/assess.py`

`_get_conn()` uses sync `psycopg2`, which blocks the uvicorn event loop on
every assess request. Migrate to `asyncpg` using the same pattern as
`srave-api`.

### C1 — Replace psycopg2 with asyncpg in assess router

- Add `asyncpg` to `services/billing-worker/requirements.txt`
- Remove `psycopg2-binary` from `requirements.txt` and from the
  `test-billing-worker` CI install step
- Rewrite `assess()` as `async def` using `asyncpg.create_pool` or a
  per-request connection via `asyncpg.connect`
- Update `billing-worker/main.py` to wire a pool via lifespan (same pattern
  as `multilateral-api/main.py`)
- Update `tests/test_smoke.py` mocks accordingly

**Acceptance:** `pytest services/billing-worker/tests -v` passes; no
`psycopg2` import remains in the billing-worker service.

---

## Track D — OpenAPI Completeness

**File:** `docs/openapi.yaml`

Currently documents 3 of ~20 endpoints. Expand to cover all routes across
`srave-api`, `spatial-worker`, `billing-worker`, `multilateral-api`, and
`voice-service`.

### D1 — Expand openapi.yaml to full surface

Add paths for:

| Router | Endpoints to add |
|---|---|
| `auth` | `POST /auth/token` |
| `spatial` | `GET /spatial/ingest/{job_id}`, `GET /spatial/lga/{lga_id}/changes` |
| `audit` | `GET /audit/lga/{lga_id}/buildings`, `GET /audit/lga/{lga_id}/collections`, `POST /audit/snapshot`, `GET /audit/snapshots/{lga_id}`, `GET /audit/snapshots/{lga_id}/verify-chain` |
| `field` | `GET /field/assignments/{agent_id}`, `PATCH /field/buildings/{building_id}/verify` |
| `billing` | `POST /billing/assess/{building_id}`, `GET /billing/assessment/{assessment_id}`, `GET /billing/lga/{lga_id}/assessments`, `POST /billing/voice-notice/{assessment_id}` |
| `admin` | `GET /admin/tax-rates/{lga_id}`, `PUT /admin/tax-rates/{lga_id}` |
| `privacy` | `GET /privacy/dsar/{phone}`, `DELETE /privacy/dsar/{phone}` |
| `webhooks` | `POST /billing/webhook/whatsapp`, `POST /billing/webhook/flutterwave`, `POST /billing/webhook/paystack` |
| `multilateral` | `GET /multilateral/export/ocds`, `GET /.well-known/signing-key.pub` |
| `voice` | `POST /voice/notice/{assessment_id}` |

Add all missing request/response schemas to `components/schemas`.

**Acceptance:** Every implemented endpoint has an entry in `openapi.yaml`.
Validate with `npx @redocly/cli lint docs/openapi.yaml`.

---

## Track E — Flutter CI & Widget Tests

### E1 — Add `flutter test` job to `ci.yml`

**File:** `.github/workflows/ci.yml`

```yaml
test-flutter:
  runs-on: ubuntu-latest
  needs: lint
  defaults:
    run:
      working-directory: services/field-agent-app
  steps:
    - uses: actions/checkout@v4
    - uses: subosito/flutter-action@v2
      with:
        flutter-version: "3.22.x"
    - run: flutter pub get
    - run: flutter test --coverage
```

**Acceptance:** Job appears in CI; passes once E2 tests are written.

---

### E2 — Widget tests for `MapScreen` and unit tests for `SyncService`

**Files:**
- `services/field-agent-app/test/map_screen_test.dart`
- `services/field-agent-app/test/sync_service_test.dart`

`MapScreen` tests (widget, mocked `ApiService` and `DbService`):
- Renders loading state on init
- Shows assignment count in AppBar after load
- Shows empty state when no unverified buildings

`SyncService` tests (unit, mocked `http` and `sqflite`):
- Calls `PATCH /field/buildings/{id}/verify` for each `synced=0` row
- Sets `synced=1` on HTTP 200
- Inserts into `sync_conflicts` and sets `synced=2` on HTTP 409
- Leaves `synced=0` on network error

**Acceptance:** `flutter test` passes with ≥ 7 test cases across both files.

---

## Track F — `voice-service` DB Lookup

**File:** `services/voice-service/main.py`

Currently the caller (`billing.py`) must pass `owner_phone`, `owner_name`,
`address`, `amount_due_ngn`, and `payment_link` in the request body. If any
field is missing the voice notice silently sends with empty values.

### F1 — Add DB pool to voice-service and look up assessment by ID

- Add lifespan with `asyncpg.create_pool` to `voice-service/main.py`
- In `voice_notice()`, fetch the assessment row from `tax_assessments JOIN
  detected_buildings JOIN tax_roll` using `assessment_id`
- Use DB values as defaults; allow request body fields to override
- Add `asyncpg` to `services/voice-service/requirements.txt`

**Acceptance:** `POST /voice/notice/42` with an empty body still produces a
correct voice notice if assessment 42 exists in DB.

---

## Track G — Branch Protection

Manual step — no code change required.

### G1 — Enable required status checks on `main`

In GitHub → Settings → Branches → `main` → Branch protection rules:

- [x] Require status checks to pass before merging
- Required checks: `lint`, `test-api`, `test-spatial-worker`,
  `test-billing-worker`, `test-multilateral-api`
- [x] Require branches to be up to date before merging
- [x] Do not allow bypassing the above settings

Add `test-flutter` to required checks once E1/E2 are merged.

---

## Sprint Summary

| ID | Track | Effort | Blocker? |
|---|---|---|---|
| A1 | Fix Dockerfiles (5 files) | S | Yes — deploy broken without this |
| A2 | Fix `deploy.yml` build context | XS | Yes |
| A3 | Fix `docker-compose.yml` build context | XS | Yes |
| B1 | Add `spatial-celery` to Compose | XS | Yes — spatial pipeline dead without this |
| B2 | Add `billing-celery` to Compose | XS | No |
| B3 | Update `deploy-hooks.md` | XS | No |
| C1 | Migrate billing-worker to asyncpg | M | No |
| D1 | Expand `openapi.yaml` | M | No |
| E1 | Add `flutter test` CI job | XS | No |
| E2 | Write MapScreen + SyncService tests | M | No |
| F1 | voice-service DB lookup | S | No |
| G1 | Enable branch protection (manual) | — | No |

**Effort key:** XS < 30 min · S < 2 h · M < 4 h

**Recommended execution order:** A1 → A2 → A3 → B1 → B2 → C1 → F1 → D1 → E1 → E2 → B3/G1
