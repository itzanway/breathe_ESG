# Breathe ESG — Data Ingestion & Review Platform

Prototype for Breathe ESG's enterprise client onboarding.
Ingests SAP fuel/procurement, utility electricity, and corporate travel data.
Normalises, flags suspicious rows, and provides analyst review workflow.

## Live demo
[Deployed on Railway — see submission email]

## Local setup (backend)

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python seed_data.py
python manage.py runserver
```

## Local setup (frontend)

```bash
cd frontend
npm install
npm run dev   # proxies /api to localhost:8000
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/health/ | Health check |
| GET | /api/summary/ | Dashboard counts |
| POST | /api/ingest/sap/ | Upload SAP CSV |
| POST | /api/ingest/utility/ | Upload utility CSV |
| POST | /api/ingest/travel/ | Upload travel JSON |
| GET | /api/records/ | List records (filterable) |
| POST | /api/records/{id}/approve/ | Approve a record |
| POST | /api/records/{id}/reject/ | Reject a record |
| GET | /api/batches/ | List ingestion batches |
| POST | /api/batches/{id}/lock/ | Lock approved records |

## Sample data

See `sample_data/` for:
- `sap_sample.csv` — SAP flat file with German column headers and mixed units
- `utility_sample.csv` — DISCOM portal export with kWh and MWh rows
- `travel_sample.json` — Concur/Navan-style JSON with flights, hotels, ground

## Docs

- `docs/MODEL.md` — Data model decisions
- `docs/DECISIONS.md` — Ambiguity resolutions
- `docs/TRADEOFFS.md` — What was deliberately not built
- `docs/SOURCES.md` — Real-world format research
