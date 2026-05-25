# Breathe ESG — Data Ingestion & Review Platform

A full-stack web application for enterprise ESG data ingestion, normalisation, and analyst review. Built for Breathe ESG's client onboarding workflow — ingests raw emissions data from SAP, utility providers, and corporate travel systems, flags suspicious records, and provides a structured approve/reject workflow for analysts.

**Live:** [breatheesg-production.up.railway.app](https://breatheesg-production.up.railway.app)

---

## What it does

Companies generate emissions data across three GHG Protocol scopes:

- **Scope 1** — Direct emissions from fuel combustion (diesel, petrol, LPG etc.)
- **Scope 2** — Purchased electricity from utility providers
- **Scope 3** — Value chain emissions from corporate travel (flights, hotels, ground transport)

This platform ingests raw files from each source, normalises units to SI standards (litres, kWh, km), auto-flags suspicious rows, and gives analysts a review dashboard to approve or reject records before locking them for audit.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React (Vite) |
| Backend | Django + Django REST Framework |
| Static serving | WhiteNoise |
| WSGI server | Gunicorn |
| Database | SQLite (file-based, persists in container) |
| Deployment | Railway (Docker) |

---

## Project Structure

```
breathe_ESG/
├── frontend/               # React app (Vite)
│   ├── src/
│   │   ├── App.jsx         # Main UI — dashboard, upload, batches tabs
│   │   ├── api.js          # All fetch calls to Django API
│   │   └── main.jsx        # Entry point
│   ├── vite.config.js
│   └── package.json
│
├── backend/                # Django project
│   ├── core/
│   │   ├── settings.py     # Django config
│   │   ├── urls.py         # API routes + SPA catch-all
│   │   └── wsgi.py
│   ├── ingestion/
│   │   ├── models.py       # Client, IngestionBatch, EmissionRecord, AuditLog
│   │   ├── views.py        # All API endpoint logic
│   │   ├── parsers.py      # SAP CSV, Utility CSV, Travel JSON parsers
│   │   └── serializers.py
│   ├── seed_data.py        # Seeds demo data on first run
│   └── requirements.txt
│
├── sample_data/            # Test files to upload via the UI
│   ├── sap_sample.csv
│   ├── utility_sample.csv
│   └── travel_sample.json
│
├── Dockerfile              # Multi-stage: Node build → Python serve
├── entrypoint.sh           # migrate → seed → gunicorn
└── railway.toml            # Railway deployment config
```

---

## Local Development

### Prerequisites

- Python 3.10+
- Node.js 18+

### Backend

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python seed_data.py        # loads 12 demo records across 3 batches
python manage.py runserver # runs on http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # runs on http://localhost:5173, proxies /api → localhost:8000
```

Open `http://localhost:5173` in your browser.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health/` | Health check |
| `GET` | `/api/summary/` | Dashboard counts by status and scope |
| `GET` | `/api/records/` | List records (supports filters below) |
| `POST` | `/api/records/{id}/approve/` | Approve a record |
| `POST` | `/api/records/{id}/reject/` | Reject a record |
| `GET` | `/api/batches/` | List ingestion batches |
| `POST` | `/api/batches/{id}/lock/` | Lock all approved records in a batch |
| `POST` | `/api/ingest/sap/` | Upload SAP CSV file |
| `POST` | `/api/ingest/utility/` | Upload utility CSV file |
| `POST` | `/api/ingest/travel/` | Upload travel JSON file |
| `GET` | `/api/clients/` | List clients |

### Record filters (`GET /api/records/`)

| Param | Values |
|-------|--------|
| `review_status` | `pending`, `suspicious`, `approved`, `rejected` |
| `source` | `sap`, `utility`, `travel` |
| `scope` | `1`, `2`, `3` |
| `client` | client slug (e.g. `demo`) |

### Approve / Reject payload

```json
{
  "reviewer": "analyst_name",
  "note": "Optional review note"
}
```

---

## Data Ingestion

### SAP CSV (Scope 1 — Fuel & Procurement)

Accepts both English and German SAP column headers. Fuel rows (diesel, petrol, LPG, etc.) are classified as Scope 1 and normalised to litres. All other procurement rows are classified as Scope 3.

Supported columns (English or German equivalents):

```
doc_date, doc_number, plant, material, quantity, unit, vendor, description
```

Example:
```csv
doc_date,doc_number,plant,material,quantity,unit,vendor,description
2024-01-15,4900012345,PL01,DIESEL001,500,L,VENDOR_A,Diesel Fuel
```

### Utility CSV (Scope 2 — Electricity)

Normalises all energy units (kWh, MWh, GWh, MJ etc.) to kWh.

```
billing_period_start, consumption_kwh, unit, meter_id, site, supplier
```

Example:
```csv
billing_period_start,consumption_kwh,unit,meter_id,site,supplier
2024-01-01,12500,kWh,MTR-001,HQ Building,DISCOM Ltd
```

### Travel JSON (Scope 3 — Corporate Travel)

Accepts Concur/Navan-style JSON arrays. Supports `flight`, `hotel`, and `ground` booking types. Flight distances are calculated from IATA airport pairs where not provided.

```json
[
  { "type": "flight", "date": "2024-01-10", "origin": "BOM", "destination": "DEL", "booking_ref": "BK001" },
  { "type": "hotel", "date": "2024-01-10", "nights": 2, "city": "Delhi", "booking_ref": "BK002" },
  { "type": "ground", "date": "2024-01-12", "distance_km": 45, "route": "Airport-Hotel" }
]
```

---

## Suspicion Flags

Records are automatically flagged during ingestion. Flagged records get `review_status: suspicious` and are highlighted in the dashboard.

| Flag | Meaning |
|------|---------|
| `outlier_high_value` | Quantity > 100,000 litres (SAP) |
| `outlier_high_kwh` | Consumption > 500,000 kWh (utility) |
| `zero_or_negative` | Quantity ≤ 0 |
| `unparseable_date` | Date format not recognised |
| `unparseable_quantity` | Non-numeric quantity |
| `unknown_volume_unit` | Unit not in conversion table |
| `unknown_airport_pair` | IATA pair not in distance lookup |
| `missing_route` | Flight missing origin/destination |

---

## Data Model

```
Client
  └── IngestionBatch (one per file upload)
        └── EmissionRecord (one per activity row)
              └── AuditLog (one per approve/reject action)
```

**EmissionRecord** stores both raw and normalised values so the original data is never lost. Once approved and locked via `lock_batch`, records become immutable (`is_locked = true`) for auditor sign-off.

---

## Deployment (Railway)

The app is deployed as a single service on Railway using a multi-stage Dockerfile:

- **Stage 1** — Node 20 builds the React frontend into `dist/`
- **Stage 2** — Python 3.12 installs Django, copies the frontend build, runs `collectstatic`, then serves everything via Gunicorn + WhiteNoise

On startup (`entrypoint.sh`):
1. `python manage.py migrate` — applies DB migrations
2. `python seed_data.py` — seeds demo data if empty
3. `gunicorn core.wsgi` — starts the WSGI server on `$PORT`

### Environment variables (optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | hardcoded dev key | Django secret key — set a real one in production |
| `DEBUG` | `False` | Enable Django debug mode |

### Re-deploy

Push to `main` branch — Railway auto-deploys via the GitHub integration.

```bash
git push origin main
```

---

## Sample Data

The `sample_data/` folder contains ready-to-upload test files:

| File | Type | Description |
|------|------|-------------|
| `sap_sample.csv` | CSV | SAP flat file with mixed English/German headers and unit variations |
| `utility_sample.csv` | CSV | DISCOM portal export with kWh and MWh rows |
| `travel_sample.json` | JSON | Concur/Navan-style export with flights, hotels, and ground transport |

Upload them via the **Upload Data** tab in the UI to see the full ingestion and review workflow.

---

## Author

**Anway Durge** — [github.com/itzanway](https://github.com/itzanway)
