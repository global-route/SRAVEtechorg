# SRAVE External Integrations

Setup and configuration guide for every third-party service SRAVE connects to.

---

## Google Earth Engine (GEE)

Used by `spatial-worker` to pull Sentinel-2 satellite imagery.

### Setup

1. Create a Google Cloud project at https://console.cloud.google.com
2. Enable the **Earth Engine API**
3. Create a **Service Account** with the `Earth Engine Resource Viewer` role
4. Download the JSON key file
5. Register the service account at https://signup.earthengine.google.com/#!/service_accounts

### Configuration

```env
GEE_SERVICE_ACCOUNT=srave-spatial@your-project.iam.gserviceaccount.com
GEE_KEY_FILE=/run/secrets/gee_key.json
```

Mount the key file as a Docker secret or volume:

```yaml
# docker-compose.yml
spatial-worker:
  volumes:
    - ./secrets/gee_key.json:/run/secrets/gee_key.json:ro
```

### What SRAVE uses

- `COPERNICUS/S2_SR_HARMONIZED` — Sentinel-2 Surface Reflectance, last 90 days
- Bands B4 (Red), B3 (Green), B2 (Blue) at 10m resolution
- `ee.data.getPixels()` for direct GeoTIFF export (avoids Drive/Cloud Storage)
- Max cloud cover: 20% (configurable)

### Quotas

GEE free tier: 100,000 EECU-seconds/month. A single LGA ingest (~2048×2048px) uses approximately 50–200 EECU-seconds depending on cloud filtering. Monitor at https://console.cloud.google.com/earth-engine.

---

## WhatsApp Business Cloud API

Used by `billing-worker` to send tax demand notices and payment reminders,
and by `voice-service` to deliver voice notes.

### Setup

1. Create a Meta Business account at https://business.facebook.com
2. Create a WhatsApp Business app at https://developers.facebook.com
3. Add a phone number and complete business verification
4. Create message templates:
   - `tax_demand_notice` — body with 5 parameters: owner_name, address, amount, payment_link, ref
   - `tax_payment_reminder` — body with 4 parameters: owner_name, address, amount, payment_ref
5. Get the **Phone Number ID** and a **Permanent Access Token** (System User token, not a temporary one)
6. Set the webhook URL to `https://api.srave.io/api/v1/billing/webhook/whatsapp`
7. Subscribe to `messages` webhook field
8. Copy the **App Secret** for webhook signature verification

### Configuration

```env
WA_API_TOKEN=<permanent_system_user_token>
WA_PHONE_NUMBER_ID=<phone_number_id>
WA_APP_SECRET=<app_secret>
```

### Template parameters

`tax_demand_notice` body component parameters (in order):
1. `{{1}}` — owner name
2. `{{2}}` — property address
3. `{{3}}` — amount due (NGN, formatted)
4. `{{4}}` — payment link URL
5. `{{5}}` — assessment reference

### Voice notes

`voice-service` uploads OGG Opus audio to the WhatsApp media endpoint
(`POST /{phone_number_id}/media`) then sends it as `type: audio` with
`voice: true`. This renders as a voice note in WhatsApp.

---

## Flutterwave

Primary payment provider. Used by `billing-worker` to generate payment links.

### Setup

1. Create an account at https://flutterwave.com
2. Complete business KYC
3. Go to **Settings → API Keys** and copy the **Secret Key**
4. Set the webhook URL to `https://api.srave.io/api/v1/billing/webhook/flutterwave`
5. Copy the **Webhook Secret Hash** (used as `FLUTTERWAVE_SECRET_KEY` for webhook verification)

### Configuration

```env
FLUTTERWAVE_SECRET_KEY=<secret_key>
```

Note: the same key is used for both payment link creation and webhook signature verification.

### What SRAVE uses

- `POST /v3/payments` — creates a hosted payment page
- `tx_ref` is set to `asmnt_{assessment_id}` for reconciliation
- `redirect_url` is `https://srave.io/payment/confirm/{assessment_id}`
- Currency: NGN

### Retry behaviour

`billing-worker/providers/flutterwave.py` retries up to 3 times with
exponential backoff (1s → 10s) on HTTP errors. After final failure, a
circuit breaker key is set in Redis for 60 seconds and Paystack is used
as fallback.

---

## Paystack

Fallback payment provider. Used when Flutterwave is unavailable.

### Setup

1. Create an account at https://paystack.com
2. Complete business verification
3. Go to **Settings → API Keys** and copy the **Secret Key**
4. Set the webhook URL to `https://api.srave.io/api/v1/billing/webhook/paystack`

### Configuration

```env
PAYSTACK_SECRET_KEY=<secret_key>
```

### What SRAVE uses

- `POST /transaction/initialize` — creates a payment link
- `reference` is set to `asmnt_{assessment_id}`
- Amount is in kobo (NGN × 100)
- Currency: NGN

---

## Mapbox

Used by the Flutter field agent app for the offline-capable map.

### Setup

1. Create an account at https://account.mapbox.com
2. Create a **public token** (starts with `pk.`)
3. Enable the **Maps SDK for Flutter** scope

### Configuration

Pass the token at build time:

```bash
flutter build apk --dart-define=MAPBOX_TOKEN=pk.your_token_here
flutter build apk --dart-define=API_BASE=https://api.srave.io/api/v1
```

Or set in `launch.json` for development:

```json
{
  "configurations": [{
    "name": "SRAVE Field Agent",
    "request": "launch",
    "type": "dart",
    "args": [
      "--dart-define=MAPBOX_TOKEN=pk.your_token_here",
      "--dart-define=API_BASE=http://10.0.2.2:8080/api/v1"
    ]
  }]
}
```

### Offline maps

The app uses `mapbox_gl: ^0.16.0`. For offline tile packs, configure
Mapbox offline regions in the app before field deployment. Tiles are cached
to device storage automatically when the agent is online.

---

## HuggingFace MMS-TTS

Used by `voice-service` for multilingual text-to-speech in 5 Nigerian languages.

### Models

| Language | Model ID | HuggingFace |
|---|---|---|
| Yoruba | `facebook/mms-tts-yor` | https://huggingface.co/facebook/mms-tts-yor |
| Igbo | `facebook/mms-tts-ibo` | https://huggingface.co/facebook/mms-tts-ibo |
| Hausa | `facebook/mms-tts-hau` | https://huggingface.co/facebook/mms-tts-hau |
| Urhobo | `facebook/mms-tts-urh` | https://huggingface.co/facebook/mms-tts-urh |
| Pidgin | `facebook/mms-tts-pcm` | https://huggingface.co/facebook/mms-tts-pcm |

### Pre-loading models

Models are downloaded automatically on first request if the container has
internet access. They cache to `/models` (Docker volume `srave-voice-models`).

To pre-populate before going live:

```bash
docker compose exec voice-service python3 -c "
from tts.engine import _load_model
for lang in ['yoruba','igbo','hausa','urhobo','pidgin']:
    _load_model(lang)
    print(f'{lang} ready')
"
```

### Audio pipeline

1. Text rendered from language template (`tts/engine.py`)
2. MMS-TTS model generates WAV waveform (PyTorch inference)
3. WAV converted to OGG Opus via pydub + FFmpeg (WhatsApp voice note format)
4. OGG bytes uploaded to WhatsApp media API
5. Voice note sent to owner's phone

No audio files are written to disk — all processing is in-memory.

---

## World Bank SFTAS / UN-Habitat

SRAVE's multilateral reporting endpoint is designed for direct submission to
World Bank SFTAS (States Fiscal Transparency, Accountability and Sustainability)
and UN-Habitat verification programs.

### Endpoint

```
GET https://api.srave.io/api/v1/multilateral/verify
```

No authentication required. Returns a JSON-LD payload with:
- `property_formalization_index` — verified buildings / total detected
- `igr_growth_rate_yoy` — year-on-year IGR growth
- `digitized_cadastral_records` — total detected buildings
- `chain_head_hash` — latest audit snapshot hash
- `signature_hash` — SHA-256 of the metrics payload
- `public_key_url` — Ed25519 public key for signature verification

### Ed25519 signing key setup

```bash
# Generate key pair
openssl genpkey -algorithm ed25519 -out signing.key
openssl pkey -in signing.key -pubout -out signing.pub

# Mount as Docker secret
docker secret create srave_signing_key signing.key
```

```env
SIGNING_KEY_PATH=/run/secrets/signing.key
```

The public key is served at `GET /.well-known/signing-key.pub` for
independent verification by multilateral institutions.
