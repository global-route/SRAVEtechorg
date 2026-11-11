# SRAVE Security Model

---

## Authentication

SRAVE uses OAuth 2.0 client credentials flow. There are no user accounts —
only machine clients registered in the `clients` DB table.

### Token issuance

```
POST /api/v1/auth/token
{ "client_id": "ogun_muni_01", "client_secret": "<secret>" }

→ { "access_token": "<JWT>", "refresh_token": "<opaque>", "expires_in": 3600 }
```

- Secrets are stored as bcrypt hashes (`bcrypt.hashpw`, cost factor 12)
- Access tokens are HS256 JWTs signed with `JWT_SECRET`
- Refresh tokens are 48-byte URL-safe random strings stored in Redis with 7-day TTL
- Refresh tokens are single-use — each refresh rotates both tokens

### JWT payload

```json
{
  "sub": "ogun_muni_01",
  "scope": "municipal",
  "lga_id": "Abeokuta South",
  "exp": 1234567890
}
```

---

## Scopes and permissions

| Scope | Who holds it | What they can access |
|---|---|---|
| `admin` | Atlantic Tech ops | Everything — no LGA restriction |
| `municipal` | LGA finance officer | Their LGA's data only (enforced by `lga_id` claim) |
| `field_agent` | Ground-truth agent | Field assignments + verify endpoint for their LGA |
| `multilateral` | World Bank / UN-Habitat | `GET /multilateral/verify` only (public, no auth required) |

### LGA tenant isolation

`require_scope_and_lga()` in `middleware/auth.py` enforces that a `municipal`
or `field_agent` token with `lga_id=X` cannot access routes for `lga_id=Y`.
`admin` tokens have `lga_id=NULL` and bypass this check.

---

## Transport security

- TLS 1.3 only — configured in `infrastructure/nginx/nginx.conf`
- HSTS: `max-age=63072000; includeSubDomains` (2 years)
- All HTTP traffic redirected to HTTPS (301)
- K3s Ingress uses cert-manager with Let's Encrypt (`letsencrypt-prod` ClusterIssuer)

---

## Security headers

Applied by `SecurityHeadersMiddleware` on every response from `srave-api`:

| Header | Value |
|---|---|
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `no-referrer` |
| `Permissions-Policy` | `geolocation=(), microphone=()` |

---

## Webhook signature verification

All three payment/messaging webhooks verify HMAC signatures before processing:

| Webhook | Header | Algorithm |
|---|---|---|
| WhatsApp | `X-Hub-Signature-256` | HMAC-SHA256 of body with `WA_APP_SECRET` |
| Flutterwave | `verif-hash` | Constant-time compare with `FLUTTERWAVE_SECRET_KEY` |
| Paystack | `x-paystack-signature` | HMAC-SHA512 of body with `PAYSTACK_SECRET_KEY` |

---

## Audit chain integrity

`audit_snapshots` is append-only:
- DB trigger `audit_snapshots_immutable` raises an exception on any UPDATE or DELETE
- `REVOKE UPDATE, DELETE ON audit_snapshots FROM srave_user`
- Each row's `ledger_entry_hash = sha256(previous_hash + canonical_json(payload))`
- `GET /audit/snapshots/{lga_id}/verify-chain` re-computes every hash and returns `chain_valid: true/false`

The multilateral verify endpoint signs the current metrics with SHA-256 and
optionally with an Ed25519 private key mounted at `SIGNING_KEY_PATH`. The
public key is served at `GET /.well-known/signing-key.pub`.

---

## Secrets management

### What must never be committed

- `.env` (gitignored)
- `gee_key.json` (GEE service account key)
- `signing.key` (Ed25519 private key)
- Any `*_SECRET*` or `*_PASSWORD*` values

### Where secrets live

| Secret | Storage |
|---|---|
| `JWT_SECRET` | `.env` → Coolify environment variable |
| `DB_PASSWORD` | `.env` → Coolify environment variable |
| `WA_API_TOKEN`, `WA_APP_SECRET` | `.env` → Coolify environment variable |
| `FLUTTERWAVE_SECRET_KEY`, `PAYSTACK_SECRET_KEY` | `.env` → Coolify environment variable |
| `GEE_KEY_FILE` | Docker secret / mounted volume at `/run/secrets/gee_key.json` |
| `SIGNING_KEY_PATH` | Docker secret / mounted volume at `/run/secrets/signing.key` |
| Coolify webhook URLs | GitHub Actions secrets (`COOLIFY_WEBHOOK_*`) |

### Rotation procedure

1. Generate new value
2. Update in Coolify environment variables
3. Trigger redeploy of affected service
4. For `JWT_SECRET`: all existing tokens are immediately invalidated — clients must re-authenticate

---

## Network isolation

- `postgres-db` and `redis-cache` do not publish ports externally (removed in sprint 11)
- All inter-service communication is over the Docker bridge network by service name
- PgBouncer is the only entry point to Postgres — direct connections from application code go through it
- Nginx is the only public-facing entry point — all services are internal

---

## Rate limiting

Configured in `infrastructure/nginx/nginx.conf`:

| Zone | Rate | Applied to |
|---|---|---|
| `ingest_limit` | 10r/m, burst 5 | `POST /api/v1/spatial/ingest` |
| `webhook_limit` | 500r/m, burst 50 | `POST /api/v1/billing/webhook/*` |
| `api_limit` | 200r/m, burst 30–40 | All other routes |

---

## Data privacy (NDPA / GDPR)

- PII columns: `tax_roll.owner_name`, `tax_roll.owner_phone`
- DSAR (Data Subject Access Request): `GET /api/v1/privacy/dsar/{phone}` returns all records
- Right to erasure: `DELETE /api/v1/privacy/dsar/{phone}` nullifies PII columns
- `audit_snapshots` contains only aggregate counts — no PII
- `tax_assessments.owner_phone` is a financial record snapshot — exempt from erasure under NDPA Article 25
- All data processing is within Nigeria (Ogun State pilot) — NDPA jurisdiction applies
- GDPR applies to any EU-resident data subjects (multilateral institution contacts)
