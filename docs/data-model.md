# SRAVE Data Model

PostgreSQL 15 + PostGIS 3.3. All tables live in the `public` schema of `srave_prod`.

---

## Entity relationships

```
lg_boundaries
    │
    └── detected_buildings (lga_id → lg_boundaries.name)
            │
            ├── tax_assessments (building_id → detected_buildings.id)
            │       └── audit_log
            │
            ├── change_detection_log (building_id → detected_buildings.id)
            ├── sync_conflicts (building_id → detected_buildings.id)
            └── failed_jobs (job_id, lga_id — soft reference)

tax_roll (lga_id → lg_boundaries.name)
    └── tax_rates (lga_id, property_type — composite PK)

clients (standalone — auth registry)
audit_snapshots (lga_id — soft reference, immutable)
```

---

## Tables

### `lg_boundaries`

LGA polygon geometries. Seeded from `database/seeds/ogun_lga_boundaries.sql`.

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | |
| `name` | TEXT NOT NULL | LGA name — used as `lga_id` throughout |
| `state` | TEXT NOT NULL | e.g. `Ogun` |
| `geom` | GEOMETRY(MULTIPOLYGON, 4326) | GIST index |

---

### `detected_buildings`

AI-detected building footprints from satellite imagery.

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | |
| `lga_id` | TEXT NOT NULL | References `lg_boundaries.name` |
| `footprint` | GEOMETRY(POLYGON, 4326) | GIST index |
| `confidence_score` | FLOAT | YOLOv8 detection confidence 0–1 |
| `property_type` | TEXT NOT NULL DEFAULT `residential_low` | `residential_low` \| `residential_high` \| `commercial` \| `industrial` |
| `verified` | BOOLEAN DEFAULT FALSE | Set by field agent via `PATCH /field/buildings/{id}/verify` |
| `scan_date` | DATE | Date of the GEE imagery used |
| `photo_url` | TEXT | Geotagged photo URL from field agent |
| `created_at` | TIMESTAMPTZ DEFAULT NOW() | |

Indexes: `lga_id`, `(lga_id, property_type)`, `(lga_id, scan_date)`, GIST on `footprint`.

---

### `tax_roll`

Registered property owners. Populated by field agent verification flow.

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | |
| `lga_id` | TEXT NOT NULL | |
| `owner_name` | TEXT | Nullable — PII, erasable via DSAR |
| `owner_phone` | TEXT | Nullable — PII, erasable via DSAR |
| `owner_language` | TEXT | `yoruba` \| `igbo` \| `hausa` \| `urhobo` \| `pidgin` |
| `address` | TEXT | |
| `geom` | GEOMETRY(POINT, 4326) | Property location — GIST index |
| `registered_at` | TIMESTAMPTZ DEFAULT NOW() | |

Indexes: `lga_id`, GIST on `geom`, `owner_phone`.

---

### `tax_rates`

Annual tax rates per LGA per property type. Default rates seeded from migration 003.

| Column | Type | Notes |
|---|---|---|
| `lga_id` | TEXT | Composite PK with `property_type` |
| `property_type` | TEXT | Composite PK |
| `annual_rate_ngn` | NUMERIC(15,2) NOT NULL DEFAULT 30000 | |

Default rates: residential_low ₦30,000 · residential_high ₦80,000 · commercial ₦200,000 · industrial ₦500,000.

---

### `tax_assessments`

One row per billing event. Created by `POST /billing/assess/{building_id}`.

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | |
| `building_id` | INT NOT NULL → `detected_buildings.id` | |
| `owner_phone` | TEXT | Snapshot of phone at assessment time |
| `amount_due` | NUMERIC(15,2) | |
| `wa_status` | TEXT DEFAULT `pending` | `pending` \| `delivered` \| `reminder_sent` \| `read` \| `paid` |
| `payment_ref` | TEXT | `asmnt_{id}` — used as Flutterwave/Paystack tx_ref |
| `assessed_at` | TIMESTAMPTZ DEFAULT NOW() | |

---

### `audit_snapshots`

Append-only SHA-256 chained ledger. **Immutable** — DB trigger prevents UPDATE/DELETE.

| Column | Type | Notes |
|---|---|---|
| `id` | BIGSERIAL PK | |
| `lga_id` | TEXT NOT NULL | |
| `snapshot_date` | DATE NOT NULL | UNIQUE with `lga_id` |
| `ledger_entry_hash` | TEXT NOT NULL | `sha256:<hex>` |
| `previous_hash` | TEXT NOT NULL | `genesis` for first entry |
| `payload_json` | JSONB NOT NULL | Snapshot metrics |
| `created_at` | TIMESTAMPTZ DEFAULT NOW() | |

Index: `(lga_id, snapshot_date DESC)`.

---

### `audit_log`

General-purpose event log for actor actions.

| Column | Type | Notes |
|---|---|---|
| `id` | BIGSERIAL PK | |
| `actor` | TEXT NOT NULL | client_id from JWT |
| `action` | TEXT NOT NULL | e.g. `verify_building` |
| `target_id` | TEXT | |
| `payload` | JSONB | |
| `logged_at` | TIMESTAMPTZ DEFAULT NOW() | |

---

### `change_detection_log`

Structural changes detected between two scan dates.

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | |
| `building_id` | INT → `detected_buildings.id` | |
| `change_type` | TEXT NOT NULL | `new` \| `modified` \| `demolished` |
| `from_scan_date` | DATE | |
| `to_scan_date` | DATE | |
| `flagged_for_review` | BOOLEAN DEFAULT TRUE | |
| `detected_at` | TIMESTAMPTZ DEFAULT NOW() | |

---

### `sync_conflicts`

Offline sync conflicts from the Flutter field agent app.

| Column | Type | Notes |
|---|---|---|
| `id` | BIGSERIAL PK | |
| `building_id` | INT → `detected_buildings.id` | |
| `local_payload` | JSONB | What the app sent |
| `server_response` | JSONB | What the API returned (409 body) |
| `resolved` | BOOLEAN DEFAULT FALSE | |
| `logged_at` | TIMESTAMPTZ DEFAULT NOW() | |

---

### `clients`

DB-backed auth client registry. Replaces static env-var map.

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | e.g. `ogun_muni_01` |
| `secret_hash` | TEXT NOT NULL | bcrypt hash |
| `scope` | TEXT NOT NULL | `municipal` \| `field_agent` \| `multilateral` \| `admin` |
| `lga_id` | TEXT | NULL for admin; enforced in JWT middleware |
| `active` | BOOLEAN NOT NULL DEFAULT TRUE | Soft revoke |
| `created_at` | TIMESTAMPTZ DEFAULT NOW() | |

Partial index on `(id) WHERE active = TRUE`.

---

### `failed_jobs`

Dead letter queue for Celery tasks that exhausted retries.

| Column | Type | Notes |
|---|---|---|
| `id` | BIGSERIAL PK | |
| `task_name` | TEXT NOT NULL | e.g. `ingest_worker.run` |
| `job_id` | TEXT NOT NULL | Redis job key |
| `lga_id` | TEXT | |
| `error` | TEXT | Exception message |
| `payload` | JSONB | Original task arguments |
| `retries` | INT NOT NULL DEFAULT 0 | |
| `replayed` | BOOLEAN NOT NULL DEFAULT FALSE | |
| `failed_at` | TIMESTAMPTZ DEFAULT NOW() | |

Indexes: `lga_id`, partial on `(replayed) WHERE replayed = FALSE`.

---

## Key spatial queries

### Revenue gap (used by `GET /audit/lga/{lga_id}/gap-analysis`)

```sql
SELECT
    COUNT(db.id)                                            AS total_detected,
    COUNT(tr.id)                                            AS registered,
    COUNT(db.id) - COUNT(tr.id)                             AS gap,
    COALESCE(SUM(COALESCE(tr2.annual_rate_ngn, 30000)), 0)  AS estimated_gap_ngn
FROM detected_buildings db
LEFT JOIN tax_roll tr
    ON ST_DWithin(db.footprint::geography, tr.geom::geography, 15)
LEFT JOIN tax_rates tr2
    ON tr2.lga_id = db.lga_id AND tr2.property_type = db.property_type
WHERE db.lga_id = $1
  AND db.verified = true;
```

### Change detection — new structures

```sql
SELECT COUNT(*) FROM detected_buildings new_b
WHERE new_b.lga_id = $1 AND new_b.scan_date = $2::date
  AND NOT EXISTS (
      SELECT 1 FROM detected_buildings old_b
      WHERE old_b.lga_id = $1 AND old_b.scan_date = $3::date
        AND ST_DWithin(new_b.footprint::geography, old_b.footprint::geography, 5)
  );
```

---

## NDPA / GDPR compliance

- `owner_name` and `owner_phone` on `tax_roll` are the only PII columns.
- `DELETE /api/v1/privacy/dsar/{phone}` nullifies both columns (`UPDATE tax_roll SET owner_phone=NULL, owner_name=NULL WHERE owner_phone=$1`).
- `audit_snapshots` stores only aggregate counts — no PII.
- `tax_assessments.owner_phone` is a snapshot at assessment time; it is not nullified by DSAR (assessment records are financial records, exempt under NDPA Article 25).
