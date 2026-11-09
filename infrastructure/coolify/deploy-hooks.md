# Coolify Deploy Hooks

Each service has a Coolify webhook URL stored as a GitHub Actions secret.

| Service | Secret Name |
|---|---|
| core-api | `COOLIFY_WEBHOOK_CORE_API` |
| spatial-ingestion | `COOLIFY_WEBHOOK_SPATIAL` |
| billing-service | `COOLIFY_WEBHOOK_BILLING` |
| multilateral-api | `COOLIFY_WEBHOOK_MULTILATERAL` |

Trigger a manual redeploy:
```bash
curl -X POST $COOLIFY_WEBHOOK_CORE_API
```
