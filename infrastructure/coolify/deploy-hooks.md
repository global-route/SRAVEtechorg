# Coolify deployment

Coolify is used to trigger deployments; it is not an SRAVE application
dependency. The GitHub Actions workflow builds service images, pushes them to
GHCR, then calls the matching Coolify webhook. Configure each Coolify resource
to use the corresponding image and ensure its webhook redeploys that resource.

| Service | Secret Name |
|---|---|
| api | `COOLIFY_WEBHOOK_API` |
| spatial-worker | `COOLIFY_WEBHOOK_SPATIAL` |
| billing-worker | `COOLIFY_WEBHOOK_BILLING` |
| multilateral-api | `COOLIFY_WEBHOOK_MULTILATERAL` |
| voice-service | `COOLIFY_WEBHOOK_VOICE` |

Store the webhook URLs as GitHub Actions secrets; do not commit them. To
manually trigger a redeploy from a shell where the URL is set:

```bash
curl --fail-with-body --request POST "$COOLIFY_WEBHOOK_API"
```

## Build-context requirement

The current GitHub Actions workflow sets `services/<service>` as the Docker
build context, while each service's `requirements.txt` references the root
`requirements-base.txt` with `../../requirements-base.txt`. Docker builds
cannot access files outside their build context. Update the workflow and
Compose build configuration to use the repository root as the context and
select the service Dockerfile, or make each service's requirements self-
contained, before relying on these image builds.

The Compose stack also does not currently start a Celery worker process for
the spatial task definitions. Deploy a separate worker command/container
before expecting queued ingestion or extraction tasks to run.
