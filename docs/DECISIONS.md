# DECISIONS.md — Every Ambiguity Resolved

## Source format choices

### SAP: Flat file (CSV), not IDoc or OData

**What I researched:** SAP exports data in four main ways — IDoc (EDI-style XML/flat), BAPI (function module calls), OData (REST-like, used in S/4HANA Fiori), and flat file reports (ALV grid exports, SE16 table dumps, SQVI query exports as CSV/TXT).

**What I chose:** Flat file CSV via transaction SE16N or ALV grid export.

**Why:** IDoc requires a dedicated SAP PI/PO middleware layer and a receiving system configured as a partner — far beyond a four-day prototype. OData requires S/4HANA and OAuth setup with the client's SAP instance. BAPI requires a live RFC connection. Flat file is what a sustainability lead at an enterprise client actually sends over — they export from SE16N or run a standard report (GR55, MB52, ME2M) and email the CSV. This is realistic. Every enterprise SAP user can produce this without IT involvement.

**What I handle:** Movement type 101 (goods receipt) and 201 (goods issue to cost centre) rows from table MSEG/EKBE, focusing on fuel materials identified by description keyword matching. I ignore internal transfers (movement type 301/303) and returns (122).

**What I ignored:** Plant maintenance orders, asset procurement, and service entry sheets — these require different tables (AUFK, ANLA, ESLL) and Scope 3 category assignments that need client-specific configuration.

---

### Utility: CSV portal export, not PDF or API

**What I researched:** Utilities expose data three ways — PDF bills (the most common), portal CSV downloads (ESMI/Green Button in the US, similar in India via state DISCOMs), and APIs (Green Button Connect in the US; rare in India).

**What I chose:** CSV portal export.

**Why:** PDF parsing (especially for utility bills with varying layouts by DISCOM) requires OCR or vendor-specific parsers — brittle and out of scope. Green Button / utility APIs are US-centric and not available for most Indian DISCOMs (BESCOM, BSES, etc.). CSV exports are available from almost every utility portal today, are machine-readable, and are what a facilities manager actually downloads month-to-month.

**What I handle:** Columns for billing period start, consumption in kWh (or MWh, converted), meter ID, and site. I handle billing periods that don't align to calendar months by using the period start date as the activity date.

**What I ignored:** Reactive power charges, tariff band breakdowns, demand charges, and time-of-use splits. These matter for cost analysis but not for Scope 2 emissions (which only need total kWh consumed).

---

### Travel: JSON from corporate travel platform, not CSV

**What I researched:** Concur (SAP) exposes an Expense Report API and a Travel Itinerary API (v2). Navan (formerly TripActions) has a REST API with a `/trips` endpoint. Both return JSON. CSV exports from both platforms also exist but lose structured fields like origin/destination airport codes (they appear as concatenated strings in CSV).

**What I chose:** JSON file upload mimicking a Navan/Concur `/trips` export.

**Why:** JSON preserves the structure: `type`, `origin`, `destination` as discrete fields rather than "LHR to JFK" in a single text column. Airport codes in discrete fields allow distance lookup. The Concur API requires OAuth2 with the client's Concur tenant — not feasible for a prototype. Instead we accept a JSON file that mirrors the API response shape.

**What I handle:** Flights (with airport-code-based distance lookup for ~10 common routes), hotels (night counts), and ground transport (distance in km or miles). For unknown airport pairs, we flag the record rather than silently dropping it.

**What I ignored:** Rail-specific emission factors, car rental vs. taxi distinction for ground transport, cabin class (business class has ~3x the emission factor of economy — a significant omission noted in TRADEOFFS.md), and multi-leg itineraries stored as separate bookings.

---

## Other decisions

### SQLite not Postgres

For the prototype, SQLite is fine — the dataset is small, there's no concurrent write load, and Railway provides Postgres for free if needed. The migration to Postgres is `DATABASE_URL` + `psycopg2` — one config change.

### Single demo client, no auth

Adding per-user authentication (Django sessions, token auth, or OAuth) would take a day alone. The PM said "build a prototype" — I chose to put that day into the data model and parsers instead. The system is designed for multi-tenancy (every row has a `client` FK); auth is the missing layer.

### Approve/reject at row level, not batch level

You could approve an entire batch at once. I chose row-level review because the brief specifically says "analysts can see what came in, what failed, what looks suspicious." Row-level lets analysts approve the clean rows and reject/flag the suspicious ones, then ask the client to fix and re-upload just the bad ones.

### What I would ask the PM

1. How do clients handle corrections — do they re-upload the whole file, or send a diff? This affects whether we version batches or upsert.
2. Do we need Scope 3 Category 1 (purchased goods) from the SAP procurement rows, or just fuel? Category 1 requires spend-based emission factors and a different data flow.
3. What's the emission factor source? DEFRA, EPA, ecoinvent, or client-specific? This determines how we structure the calculation layer.
4. Is there a required data format for the auditors, or do they access this system directly?
5. Multi-currency? SAP procurement rows often come in local currency. Do we normalise to USD/EUR, and at what exchange rate?
