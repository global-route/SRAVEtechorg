# SRAVE — Spatial Revenue & Asset Verification Engine

> AI-powered property tax infrastructure for sub-national governments in emerging markets.

SRAVE bridges satellite remote sensing, computer vision, and automated billing to close the property tax gap in cities where most real estate is unmapped and off the tax roll. Built for municipal governments, verified by multilateral institutions.

---

## The Problem

Sub-national governments across West Africa capture a fraction of their theoretical property tax potential. Local councils rely on manual street-by-street enumeration — notebooks, cash collectors, and outdated analog rolls. The result: broke councils, underfunded infrastructure, and zero fiscal transparency for institutions like the World Bank or UN-Habitat.

---

## What SRAVE Does

### 1. Satellite Property Detection
Ingests high-resolution optical imagery (Sentinel-2, PlanetScope) via Google Earth Engine and runs AI computer vision models (SAM, YOLOv8) to automatically detect and segment every rooftop in a Local Government Area. No field crew required for the initial sweep.

### 2. Revenue Gap Analysis
Performs a PostGIS spatial join between AI-detected building footprints and the existing municipal tax roll. The delta — unregistered structures — is quantified into a precise annual revenue gap in local currency. Example: 84,500 detected buildings vs. 14,200 registered taxpayers = ₦3.5B uncaptured annually.

### 3. Field Agent Ground-Truthing
A Flutter mobile app (offline-first, Mapbox GL) routes field agents directly to AI-flagged unregistered properties for physical verification, geotagged photo capture, and owner contact collection — without requiring constant connectivity.

### 4. Automated WhatsApp Billing
Verified properties trigger an automated WhatsApp demand notice via the WhatsApp Business Cloud API — including property details, amount due, and a secure direct-to-treasury payment link (Flutterwave / Paystack). No cash, no touts, no leakage.

### 5. Multilateral Audit & Verification API
A dedicated OpenAPI 3.0 endpoint packages anonymized compliance metrics — property formalization index, IGR growth rate, digitized cadastral records — for direct submission to World Bank SFTAS and UN-Habitat verification programs. Responses are SHA-256 signed for immutability.

---

## Technology Stack

| Layer | Stack |
|---|---|
| Geospatial & Remote Sensing | Google Earth Engine, Sentinel-2, PlanetScope, GeoPandas, Rasterio |
| AI / Computer Vision | SAM, YOLOv8, PyTorch, FastAPI |
| Backend API | Go (Fiber/Gin), PostgreSQL + PostGIS, Redis |
| Mobile (Field Agent) | Flutter, SQLite (offline-first), Mapbox GL JS |
| Billing & Payments | WhatsApp Business Cloud API, Flutterwave, Paystack |
| Multilateral Reporting | OpenAPI 3.0, JSON-LD, OCDS |
| Infrastructure | Hetzner VPS, Coolify/Dokploy, Docker, K3s, GitHub Actions |
| Security | TLS 1.3, mTLS, OAuth 2.0, JWT, AES-256, RBAC |

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
- Aligned with UN SDG 9 (Infrastructure), SDG 11 (Sustainable Cities), SDG 16 (Accountable Institutions)

---

## Contact

Built by **Atlantic Tech Innovations**
For partnerships, pilots, or grant collaborations — open an issue or reach out via the organization profile.
