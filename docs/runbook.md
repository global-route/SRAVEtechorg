# SRAVE Operations Runbook

Operational procedures for the production stack. All commands assume you are
on the Coolify host or have SSH access to it.

---

## Stack overview

```
Nginx (TLS 1.3) → srave-api:8080
                → spatial-worker:8001
                → billing-worker:8002
                → multilateral-api:8003
                → voice-service:8004
                → dashboard:3001

All services → pgbouncer:5432 → postgres-db (PostGIS 15)
All services → redis-cache:6379 (512MB LRU cap)
spatial-celery, billing-celery → Redis broker
```

---

## Deploy

### Normal deploy (CI-triggered)

Push to `main` → GitHub Actions builds images → pushes to GHCR → calls Coolify webhooks.
No manual action required if all CI jobs pass.

### Manual redeploy of a single service

```bash
curl --fail-with-body --request POST "$COOLIFY_WEBHOOK_API"
curl --fail-with-body --request POST "$COOLIFY_WEBHOOK_SPATIAL"
curl --fail-with-body --request POST "$COOLIFY_WEBHOOK_BILLING"
curl --fail-with-body --request POST "$COOLIFY_WEBHOOK_MULTILATERAL"
curl --fail-with-body --request POST "$COOLIFY_WEBHOOK_VOICE"
```

### Local stack

```bash
make up          # build + start all containers
make down        # stop all containers
make build       # rebuild images without starting
make migrate     # run pending migrations
make migrate-fresh  # drop all + re-run from scratch (dev only)
```

---

## Rollback

### Roll back a service image

```bash
# Pull a specific tag
docker pull ghcr.io/atlantic-tech/srave-api:<tag>

# Update the Coolify resource to use that tag, then redeploy
curl --fail-with-body --request POST "$COOLIFY_WEBHOOK_API"
```

### Roll back a migration

```bash
make migrate-down   # rolls back the last migration
```

To roll back multiple steps:

```bash
docker compose run --rm srave-api python -m alembic downgrade -2
```

---

## Database

### Connect

```bash
# Via PgBouncer (application path)
psql -h localhost -p 5432 -U srave_user -d srave_prod

# Direct to Postgres (admin/maintenance only)
docker compose exec postgres-db psql -U srave_user -d srave_prod
```

### Backup

```bash
docker compose exec postgres-db pg_dump -U srave_user srave_prod \
  | gzip > srave_prod_$(date +%Y%m%d_%H%M%S).sql.gz
```

Schedule daily via cron on the host:

```cron
0 2 * * * docker compose -f /opt/srave/docker-compose.yml exec -T postgres-db \
  pg_dump -U srave_user srave_prod | gzip > /backups/srave_$(date +\%Y\%m\%d).sql.gz
```

### Restore

```bash
gunzip -c srave_prod_20240101_020000.sql.gz \
  | docker compose exec -T postgres-db psql -U srave_user -d srave_prod
```

### Seed Ogun LGA boundaries

```bash
make seed-ogun
```

---

## Model volumes

`spatial-worker` and `voice-service` require model files on `/models` volumes.
These are not in the repository.

### spatial-worker models

```bash
# Copy YOLOv8 weights
docker cp yolov8m-seg.pt $(docker compose ps -q spatial-worker):/models/

# Copy SAM checkpoint
docker cp sam_vit_h_4b8939.pth $(docker compose ps -q spatial-worker):/models/
```

Download links:
- YOLOv8m-seg: https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8m-seg.pt
- SAM ViT-H: https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth

### voice-service models

MMS-TTS models are downloaded automatically from HuggingFace on first request
if the container has internet access. They cache to `/models`. To pre-populate:

```bash
docker compose exec voice-service python3 -c "
from tts.engine import _load_model
for lang in ['yoruba','igbo','hausa','urhobo','pidgin']:
    _load_model(lang)
    print(f'{lang} loaded')
"
```

---

## Redis

### Check memory usage

```bash
docker compose exec redis-cache redis-cli info memory | grep used_memory_human
```

### Inspect a job

```bash
docker compose exec redis-cache redis-cli get "job:<job_id>"
```

### Clear all job keys (dev only)

```bash
docker compose exec redis-cache redis-cli --scan --pattern "job:*" \
  | xargs docker compose exec -T redis-cache redis-cli del
```

### Check circuit breaker state

```bash
docker compose exec redis-cache redis-cli exists "circuit:flutterwave"
docker compose exec redis-cache redis-cli exists "circuit:paystack"
docker compose exec redis-cache redis-cli exists "circuit:whatsapp"
```

---

## Celery

### Check active tasks (Flower)

Open http://localhost:5555 (or https://api.srave.io/flower if Nginx-proxied).
Basic auth: `FLOWER_USER` / `FLOWER_PASSWORD` from `.env`.

### Inspect via CLI

```bash
docker compose exec spatial-celery celery -A ingestion.tasks.celery_app inspect active
docker compose exec spatial-celery celery -A ingestion.tasks.celery_app inspect reserved
```

### Replay a failed job

```bash
curl -s -X POST https://api.srave.io/api/v1/admin/failed-jobs/<job_id>/replay \
  -H "Authorization: Bearer <admin_token>"
```

### List failed jobs

```bash
curl -s "https://api.srave.io/api/v1/admin/failed-jobs?replayed=false" \
  -H "Authorization: Bearer <admin_token>" | jq .
```

---

## Signing key

### Generate Ed25519 key pair (run once on production host)

```bash
mkdir -p secrets
openssl genpkey -algorithm ed25519 -out secrets/signing.key
openssl pkey -in secrets/signing.key -pubout -out secrets/signing.pub
chmod 600 secrets/signing.key
```

The `secrets/` directory is gitignored. The key is mounted read-only into `multilateral-api` at `/run/secrets/signing.key`. The public key is served at `GET /.well-known/signing-key.pub`.

---

## Auth

### Create a new municipal client

```bash
# 1. Generate bcrypt hash
python3 -c "import bcrypt; print(bcrypt.hashpw(b'<secret>', bcrypt.gensalt()).decode())"

# 2. Create via API (requires admin token)
curl -s -X POST https://api.srave.io/api/v1/admin/clients \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"id":"ogun_muni_01","secret":"<secret>","scope":"municipal","lga_id":"Abeokuta South"}'
```

### Revoke a client

```bash
curl -s -X DELETE https://api.srave.io/api/v1/admin/clients/ogun_muni_01 \
  -H "Authorization: Bearer <admin_token>"
```

---

## Monitoring

### Grafana

http://localhost:3000 — admin / `GRAFANA_PASSWORD`

Key panels:
- Request rate per service
- Error rate (5xx) per service
- p95 latency per service
- Celery active tasks
- Daily collections (NGN)

### Logs

All services emit structured JSON logs. Aggregate with any log shipper
(Loki, Datadog, CloudWatch). Each log line includes `service`, `request_id`,
and event-specific fields.

```bash
# Tail a service
docker compose logs -f srave-api

# Filter for errors
docker compose logs srave-api 2>&1 | grep '"level":"error"'
```

---

## Incident response

### Service is down

```bash
docker compose ps                          # check container status
docker compose logs --tail=50 <service>    # check recent logs
docker compose restart <service>           # restart single service
```

### Postgres is unreachable

```bash
docker compose exec postgres-db pg_isready -U srave_user -d srave_prod
docker compose restart postgres-db
docker compose restart pgbouncer           # restart pool after DB restart
```

### Ingest job stuck in `queued`

The Celery worker is not running or not connected to Redis.

```bash
docker compose ps spatial-celery
docker compose logs spatial-celery
docker compose restart spatial-celery
```

### WhatsApp / payment provider circuit open

```bash
# Check which circuits are open
docker compose exec redis-cache redis-cli keys "circuit:*"

# Manually clear a circuit (forces retry on next request)
docker compose exec redis-cache redis-cli del "circuit:flutterwave"
```

### Audit chain integrity failure

```bash
curl -s "https://api.srave.io/api/v1/audit/snapshots/<lga_id>/verify-chain" \
  -H "Authorization: Bearer <admin_token>" | jq .
```

If `chain_valid: false`, the `snapshots_checked` field identifies the first
broken snapshot. Do not delete or modify `audit_snapshots` rows — the table
has a DB-level immutability trigger. Investigate the snapshot at that index
for data corruption.
