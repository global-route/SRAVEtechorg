# Coolify Deployment Notes

Coolify is the self-hosted deployment and operations platform. It is not an
SRAVE runtime dependency. The GitHub Actions workflow (`deploy.yml`) builds
service images, pushes them to GHCR, then calls a per-service Coolify webhook
to trigger a redeploy.

## Webhook secrets

Configure each Coolify resource to use the corresponding GHCR image and set
its webhook URL as a GitHub Actions secret:

| Service | Secret name |
|---|---|
| `api` | `COOLIFY_WEBHOOK_API` |
| `spatial-worker` | `COOLIFY_WEBHOOK_SPATIAL` |
| `billing-worker` | `COOLIFY_WEBHOOK_BILLING` |
| `multilateral-api` | `COOLIFY_WEBHOOK_MULTILATERAL` |
| `voice-service` | `COOLIFY_WEBHOOK_VOICE` |

Never commit webhook URLs. To manually trigger a redeploy:

```bash
curl --fail-with-body --request POST "$COOLIFY_WEBHOOK_API"
```

## Known issues (tracked in [sprint-10.md](../docs/sprint-10.md))

### Build context (tasks A1–A3) — RESOLVED

All 5 Dockerfiles now copy `requirements-base.txt` from the repo root before
the service-specific `requirements.txt`. `deploy.yml` and `docker-compose.yml`
both use the repo root as build context with an explicit `dockerfile:` path.
`docker build -f services/api/Dockerfile .` from the repo root now succeeds.

### Celery workers (tasks B1–B2) — RESOLVED

`spatial-celery` and `billing-celery` service blocks are now defined in
`docker-compose.yml`. Each reuses the same image as its parent service but
runs a Celery worker command instead of uvicorn.

For Coolify, create a separate resource for each worker container pointing
to the same GHCR image with the appropriate `command` override:

| Container | Command |
|---|---|
| `spatial-celery` | `celery -A ingestion.tasks.celery_app worker --loglevel=info -Q celery --concurrency=2` |
| `billing-celery` | `celery -A routers.assess worker --loglevel=info --concurrency=2` |

Both workers require `REDIS_URL` and DB env vars from the shared `.env`.

## Image tags

All images are pushed to GHCR under `ghcr.io/atlantic-tech/<image>:latest`.
Pin to a digest or a versioned tag in production to avoid unintended rollouts.

## Model volumes

`spatial-worker` and `voice-service` expect model checkpoints on `/models`
(Docker volume `srave-model-weights` and `srave-voice-models`). These volumes
must be pre-populated before the services can run inference. Model files are
not included in the repository.

| Service | Expected files |
|---|---|
| `spatial-worker` | `/models/yolov8m-seg.pt`, `/models/sam_vit_h_4b8939.pth` |
| `voice-service` | HuggingFace MMS-TTS cache at `/models` (auto-downloaded on first request if internet access is available) |
