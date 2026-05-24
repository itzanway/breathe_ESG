# TRADEOFFS.md — Three Things Deliberately Not Built

## 1. Emission factor calculation (CO2e output)

**What it is:** Multiplying activity quantities by emission factors to produce kg CO2e — the actual number that goes to auditors and on the sustainability report.

**Why I didn't build it:** Emission factors are not static. DEFRA updates them annually. Different clients may use different factor sets (DEFRA vs EPA vs ecoinvent vs supplier-specific). The factors themselves need version control — a 2023 approval run should use 2023 factors, not 2025 ones when you reopen the report. Building a correct, auditable emission factor library is a project on its own. What I built — normalised activity data in consistent units — is the prerequisite for that calculation and the harder part to get right. The calculation layer is multiplication; the ingestion and normalisation layer is where errors hide.

**What this means for the prototype:** The dashboard shows activity quantities (litres, kWh, km), not CO2e. An analyst can see "48,200 kWh" for February but not "19.7 tCO2e." This is the most significant functional gap.

---

## 2. Authentication and role-based access

**What it is:** Login, per-user sessions, and separate roles for "uploader," "analyst," and "auditor" — so only analysts can approve, only uploaders can ingest, and auditors get a read-only view.

**Why I didn't build it:** Django's auth system is solid, but wiring it with token auth (or OAuth for enterprise SSO) and then building the frontend session management, login pages, and protected routes would consume the majority of Day 1. The brief says analysts review and sign off before data goes to auditors — that workflow exists in the data model (the `reviewed_by`, `is_locked`, and `AuditLog` fields are all there). What's missing is enforcing it at the HTTP layer. I chose to build the data model and the ingestion logic correctly instead of spending the time on auth plumbing that doesn't demonstrate ESG domain judgment.

**What this means for the prototype:** Any user can call any endpoint. In production, every write endpoint would require a valid session with the right role.

---

## 3. Real-time validation against client master data

**What it is:** Checking SAP plant codes against a client's actual plant list, validating material numbers against their material master, and resolving vendor IDs to vendor names using their vendor master — so "WERKS: MUM1" maps to "Mumbai Andheri Facility" and "LIFNR: 1000234" maps to "HPCL."

**Why I didn't build it:** This requires the client to provide their SAP master data, which is a separate data exchange with its own format (usually another flat file or an OData service call). Without it, we display raw codes (PLANT_MUM, vendor ID 1000234) and let the analyst interpret them. Adding a lookup table upload UI and a code-resolution step would be the right next step but not achievable in four days without sacrificing the quality of what was built.

**What this means for the prototype:** The `location` field shows raw plant codes and the `vendor` field shows raw vendor numbers from SAP. The `flags` system already marks rows where we couldn't resolve a code, so analysts know which rows need manual interpretation.
