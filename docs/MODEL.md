# MODEL.md — Data Model

## Overview

Four tables: `Client`, `IngestionBatch`, `EmissionRecord`, `AuditLog`.
Every row in the system can answer: who owns it, where it came from, what it contains, whether it has been reviewed, and what happened to it.

---

## Multi-tenancy

`Client` is the tenant root. Every `IngestionBatch` and every `EmissionRecord` has a foreign key to `Client`. Queries always filter by `client_id`. In this prototype we use a single demo client; in production, `Client` would tie to an authentication identity (organisation-level OAuth or API key).

We chose row-level tenancy (a `client` FK on every table) rather than separate schemas per tenant because the dataset sizes for ESG data are modest (millions of rows, not billions), and cross-tenant analytics (benchmarking, sector averages) become possible without cross-schema joins.

---

## IngestionBatch

One batch = one file upload event. It records:

- `source`: one of `sap`, `utility`, `travel`
- `filename`: original filename, preserved for traceability
- `status`: `pending → processing → done | failed`
- `row_count`, `error_count`: populated after processing
- `uploaded_at`, `processed_at`: timestamps

**Why batch tracking matters:** If a file is re-uploaded (corrected data), you get a new batch. The old records are not deleted — they can be compared. The analyst can see "batch 1 had 200 rows, batch 2 (correction) had 198 rows" and decide which to approve.

---

## EmissionRecord

The canonical normalized activity row. Design decisions:

### Scope 1/2/3 assignment

We assign scope at parse time, not at query time, because the source type mostly determines scope:

| Source | Default scope | Logic |
|--------|--------------|-------|
| SAP | Scope 1 (fuel rows) / Scope 3 (procurement) | Detect fuel via material description keywords |
| Utility | Scope 2 | All purchased electricity is Scope 2 by GHG Protocol |
| Travel | Scope 3 | Business travel is Scope 3 Category 6 |

This is stored on the record so analysts can override it if the assignment was wrong. A future version would use a configurable emission category taxonomy.

### Unit normalization

We store both the raw quantity/unit (exactly as it arrived) and the normalized quantity/unit (converted to a base unit). This means:

- Analysts can see the original value from the source system
- Computations run on consistent units (litres, kWh, km, nights)
- If the conversion factor was wrong, we can recompute without re-ingesting

Base units chosen:
- Fuel: **litres** (SAP exports in L, gal, m³ — all converted)
- Electricity: **kWh** (utility exports in kWh, MWh, GWh — all converted)
- Travel distance: **km** (Concur/Navan give miles or km — we normalise to km)
- Hotel: **nights** (no conversion needed)

### Source-of-truth tracking

Every `EmissionRecord` has:
- `batch`: FK to the ingestion batch (→ filename, source, upload time)
- `source_ref`: the document number / meter ID / booking reference from the source system
- `raw_quantity` + `raw_unit`: exactly what came in
- `created_at` + `updated_at`: Django auto timestamps
- `is_locked`: once locked, no further edits

This means for any row you can answer: "This number came from SAP document 4900012301, uploaded on 2024-04-01 as file GR55_fuel_Q1_2024.csv, with an original value of 5400 L."

### Review workflow

States: `pending → approved | rejected | suspicious`

- Parser flags suspicious rows (outlier values, unit mismatches, unknown airport pairs) and sets `review_status = suspicious` at ingest time.
- Analysts can approve or reject any non-locked row via the API.
- `reviewed_by` and `reviewed_at` are stored on the record.
- Once a batch is locked (`/api/batches/{id}/lock/`), approved records get `is_locked = True`. Locked records are immutable — the lock endpoint only runs on approved rows, so unapproved rows stay reviewable.

### flags field

`flags` is a JSON array of strings written at parse time. Examples:
- `"outlier_high_value"` — quantity > threshold
- `"unknown_airport_pair:XYZ-ABC"` — airport codes not in our lookup table
- `"unit_converted_from_gal"` — conversion happened, analyst should sanity-check
- `"unparseable_date"` — date field couldn't be parsed, defaulted to today

This drives the "suspicious" badge in the UI without needing extra tables.

---

## AuditLog

Append-only. One row per action on an `EmissionRecord`. Stores:

- `action`: string (approved, rejected, edited, locked)
- `actor`: who did it (analyst name or API key identifier)
- `before` / `after`: JSON snapshots of the changed fields
- `timestamp`: auto

This is the audit trail required for external verification. Auditors can reconstruct the full history of any record.

---

## What this model does NOT do (deliberately)

- **Emission factor lookup**: We store activity quantities, not CO2e. Applying emission factors (kg CO2e / unit) is a separate computation step that should be versioned (factors change year to year). This prototype stops at normalized activity data.
- **Real authentication**: `reviewed_by` is a plain string, not a FK to a User. Production would use Django's auth system.
- **Sub-meter or cost-centre allocation**: Electricity is recorded at site level. Splitting by floor or department requires additional data not present in standard utility exports.
