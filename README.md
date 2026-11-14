# SRAVE — Spatial Revenue & Asset Verification Engine

> AI-powered property tax infrastructure for sub-national governments in emerging markets.

SRAVE bridges satellite remote sensing, computer vision, and automated billing to close the property tax gap in cities where most real estate is unmapped and off the tax roll. Built for municipal governments, verified by multilateral institutions.

---

## The Problem

Sub-national governments across West Africa capture a fraction of their theoretical property tax potential. Lagos State collected only **₦14 billion** out of a **₦375 billion** property tax target — a 96% revenue gap — because local governments lack cadastral maps of unregistered buildings and rely entirely on manual street-by-street enumeration with notebooks and cash collectors.

---

## What SRAVE Does

### 1. Satellite Property Detection
Ingests high-resolution optical imagery (Sentinel-2, PlanetScope) via Google Earth Engine and runs AI computer vision models (SAM, YOLOv8) to automatically detect and segment every rooftop in a Local Government Area. No field crew required for the initial sweep.

### 2. Revenue Gap Analysis
Performs a PostGIS spatial join between AI-detected building footprints and the existing municipal tax roll. The delta — unregistered structures — is quantified into a precise annual revenue gap in local currency. Example: 84,500 detected buildings vs. 14,200 registered taxpayers = ₦3.5B uncaptured annually.

### 3. Field Agent Ground-Truthing
A Flutter mobile app (offline-first, Mapbox GL) routes field agents directly to AI-flagged unregistered properties for physical verification, geotagged photo capture, and owner contact collection — without requiring constant connectivity. On-device YOLOv8-nano classifies building type from camera photos.

### 4. Automated WhatsApp Billing
Verified properties trigger an automated WhatsApp demand notice via the WhatsApp Business Cloud API — including property details, amount due, and a secure direct-to-treasury payment link (Flutterwave / Paystack). Voice notes in 5 indigenous Nigerian languages (Yoruba, Igbo, Hausa, Urhobo, Pidgin) serve rural low-literacy property owners.

### 5. Multilateral Audit & Verification API
A dedicated OpenAPI 3.0 endpoint packages anonymized compliance metrics — property formalization index, IGR growth rate, digitized cadastral records — for direct submission to World Bank SFTAS and UN-Habitat verification programs. Responses are SHA-256 chained and cryptographically signed for immutability.

---

## SDG Alignment

SRAVE directly advances three United Nations Sustainable Development Goals:

| SDG | Goal | SRAVE Contribution |
|---|---|---|
| **SDG 9** | Industry, Innovation & Infrastructure | Digitises municipal property infrastructure in cities with no cadastral baseline |
| **SDG 11** | Sustainable Cities & Communities | Enables LGAs to fund urban services through formalised property tax revenue |
| **SDG 16** | Peace, Justice & Strong Institutions | Eliminates cash leakage and touts; provides cryptographically verifiable fiscal data to multilateral auditors |

SRAVE is a candidate for registration as a **Digital Public Good (DPG)** under the DPGA standard. Core spatial engine: MIT License. AI/geospatial scripts: Apache 2.0.

---

## Technology Stack

| Layer | Stack |
|---|---|
| Geospatial & Remote Sensing | Google Earth Engine, Sentinel-2, PlanetScope, GeoPandas, Rasterio |
| AI / Computer Vision | SAM, YOLOv8, PyTorch, FastAPI |
| Backend API | Python (FastAPI), PostgreSQL + PostGIS, Redis, Celery |
| Municipal Dashboard | Next.js 14, Recharts, Tailwind CSS |
| Mobile (Field Agent) | Flutter, SQLite (offline-first), Mapbox GL, TFLite |
| Billing & Payments | WhatsApp Business Cloud API, Flutterwave, Paystack |
| Voice Notices | Facebook MMS TTS (5 Nigerian languages) |
| Multilateral Reporting | OpenAPI 3.0, JSON-LD, OCDS, Ed25519 signing |
| Infrastructure | Hetzner VPS, Coolify, Docker, K3s, PgBouncer, Prometheus, Grafana |
| Security | TLS 1.3, mTLS, OAuth 2.0, JWT, AES-256, RBAC |

---

## Quick Start

```bash
git clone https://github.com/global-route/SRAVEtechorg.git
cd SRAVEtechorg
cp .env.example .env        # fill in values
make up                     # start all services
make migrate                # run DB migrations
make seed                   # load sample LGA data
```

See [docs/contributing.md](docs/contributing.md) for full setup instructions.

---

## Documentation

| Doc | Description |
|---|---|
| [Architecture Overview](docs/architecture-overview.md) | Service topology, data flow |
| [API Reference](docs/openapi.yaml) | OpenAPI 3.0 spec |
| [Data Model](docs/data-model.md) | Full DB schema |
| [Integrations](docs/integrations.md) | GEE, WhatsApp, Flutterwave, Paystack |
| [Security](docs/security.md) | mTLS, RBAC, NDPA compliance |
| [Runbook](docs/runbook.md) | Deployment and operations |
| [Roadmap](docs/roadmap.md) | Phase plan and milestones |
| [Contributing](docs/contributing.md) | Dev setup and workflow |

---

## Compliance & Licensing

- Core spatial engine and PostGIS processing: **MIT License**
- AI/Python geospatial scripts: **Apache 2.0**
- Data handling: fully compliant with the **Nigeria Data Protection Act (NDPA)** and **GDPR**
- Registered as a **Digital Public Good (DPG)** candidate under the DPGA standard

---

## Target Impact

- Sub-national governments in Nigeria (Ogun, Delta, Lagos LGAs) — initial pilot
- Replicable across any municipality with satellite coverage and a tax authority
- Aligned with UN SDG 9, SDG 11, SDG 16

---

## Contact

Built by **Atlantic Tech Innovations**
For partnerships, pilots, or grant collaborations — open an issue or reach out via the organization profile.
