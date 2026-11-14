# Coolify Deployment Notes

Coolify is the self-hosted deployment and operations platform. It is not an
SRAVE runtime dependency. The GitHub Actions workflow (`deploy.yml`) builds
service images, pushes them to GHCR, then calls a per-service Coolify webhook
to trigger a redeploy.

---

## Webhook secrets

Configure each Coolify resource to use the corresponding GHCR image and set
its webhook URL as a GitHub Actions secret:

| Service | GHCR image | Secret name |
|---|---|---|
| `api` | `ghcr.io/atlantic-tech/srave-api:latest` | `COOLIFY_WEBHOOK_API` |
| `spatial-worker` | `ghcr.io/atlantic-tech/srave-spatial:latest` | `COOLIFY_WEBHOOK_SPATIAL` |
| `billing-worker` | `ghcr.io/atlantic-tech/srave-billing:latest` | `COOLIFY_WEBHOOK_BILLING` |
| `multilateral-api` | `ghcr.io/atlantic-tech/srave-multilateral:latest` | `COOLIFY_WEBHOOK_MULTILATERAL` |
| `voice-service` | `ghcr.io/atlantic-tech/srave-voice:latest` | `COOLIFY_WEBHOOK_VOICE` |
| `dashboard` | `ghcr.io/atlantic-tech/srave-dashboard:latest` | `COOLIFY_WEBHOOK_DASHBOARD` |

Never commit webhook URLs. To manually trigger a redeploy:

```bash
curl --fail-with-body --request POST "$COOLIFY_WEBHOOK_API"
```

---

## Celery workers

`spatial-celery` and `billing-celery` reuse the same images as their parent
services but run a different command. Create separate Coolify resources for
each with the following command overrides:

| Resource | Image | Command |
|---|---|---|
| `spatial-celery` | `srave-spatial:latest` | `celery -A ingestion.tasks.celery_app worker --loglevel=info -Q celery --concurrency=2` |
| `billing-celery` | `srave-billing:latest` | `celery -A routers.assess worker --loglevel=info --concurrency=2` |

Both require the same environment variables as their parent services.

---

## Environment variables

All services share the variables defined in `.env.example`. Set them in
Coolify's environment variable panel for each resource. Key variables:

```
DB_HOST=pgbouncer          # all services connect via PgBouncer
REDIS_URL=redis://redis-cache:6379
JWT_SECRET=<strong_random>
WA_API_TOKEN=<whatsapp_token>
WA_PHONE_NUMBER_ID=<phone_id>
WA_APP_SECRET=<app_secret>
FLUTTERWAVE_SECRET_KEY=<key>
PAYSTACK_SECRET_KEY=<key>
GEE_SERVICE_ACCOUNT=<email>
GEE_KEY_FILE=/run/secrets/gee_key.json
SIGNING_KEY_PATH=/run/secrets/signing.key
PILOT_LGA=Abeokuta South
```

---

## Image tags

All images are pushed to GHCR under `ghcr.io/atlantic-tech/<image>:latest`.
Pin to a digest or a versioned tag in production to avoid unintended rollouts:

```bash
# Get the digest of the current latest
docker inspect --format='{{index .RepoDigests 0}}' ghcr.io/atlantic-tech/srave-api:latest
```

---

## Model volumes

`spatial-worker` and `voice-service` expect model checkpoints on `/models`
persistent volumes. These are not included in the repository.

| Service | Volume | Expected files |
|---|---|---|
| `spatial-worker` | `srave-model-weights` | `yolov8m-seg.pt`, `sam_vit_h_4b8939.pth` |
| `voice-service` | `srave-voice-models` | HuggingFace MMS-TTS cache (auto-downloaded) |

See [docs/runbook.md](../../docs/runbook.md#model-volumes) for pre-population
instructions.

---

## PgBouncer

All application services connect to `pgbouncer:5432` (not `postgres-db:5432`
directly). PgBouncer runs in transaction pooling mode with `max_client_conn=200`
and `default_pool_size=20`.

The `userlist.txt` at `infrastructure/pgbouncer/userlist.txt` must contain
the MD5 hash of `srave_user`'s password. Generate it:

```bash
echo -n "<password>srave_user" | md5sum
# prefix result with "md5"
```

Then update `userlist.txt`:
```
"srave_user" "md5<hash>"
```

---

## Known issues

All previously tracked deployment blockers are resolved as of phase 15.
See [docs/architecture-overview.md](../../docs/architecture-overview.md)
for the full completed phases table.
