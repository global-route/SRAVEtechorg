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

### Build context (tasks A1–A3) — OPEN

`deploy.yml` and `docker-compose.yml` set each service subdirectory as the
Docker build context. Each service `requirements.txt` references
`../../requirements-base.txt`, which is outside that context. Standalone
`docker build` and the GitHub Actions deploy job will fail with a `COPY`
path error until tasks A1–A3 are completed.

**Workaround:** `make up` works locally because Compose uses bind mounts, not
a restricted build context.

### Celery workers (tasks B1–B2) — OPEN

`docker-compose.yml` starts `spatial-worker` and `billing-worker` with
`uvicorn` only. No Celery worker process consumes from Redis, so queued
ingestion and extraction tasks never execute.

**Impact:** `POST /api/v1/spatial/ingest` returns 202 and queues a job, but
the job stays in `queued` state indefinitely.

**Fix (phase 10):** Add `spatial-celery` and `billing-celery` service blocks
to `docker-compose.yml` and corresponding Coolify resources.

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
