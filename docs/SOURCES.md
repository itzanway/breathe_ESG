# SOURCES.md — Real-World Format Research

## Source 1: SAP Fuel & Procurement

### Real-world format researched

SAP's primary export formats for procurement and inventory data are:

- **IDoc (Intermediate Document):** XML or flat-file EDI format for system-to-system integration. A fuel goods receipt would be a MATMAS or MBGMCR IDoc. Requires SAP PI/PO middleware to generate.
- **SE16N table export:** Direct table dump from MSEG (material document segment) or EKBE (purchasing document history). Exported as CSV/TXT via ALV grid "Spreadsheet" function. This is what sustainability leads actually do.
- **Standard reports:** GR55 (cost element report), MB52 (warehouse stocks), ME2M (purchase orders by material) — all exportable as CSV.
- **OData (S/4HANA):** REST-based, returns JSON. Endpoint `/sap/opu/odata/sap/MM_PUR_POITEMS_MANAGE_SRV/` for purchase orders.

**What I learned:** SAP column headers in German are the norm in many European and Indian enterprises because SAP's default language setting at installation time determines the UI language. Columns like `MENGE` (quantity), `MEINS` (unit of measure), `WERKS` (plant), `BLDAT` (document date) are standard ABAP field names. Enterprise clients often have customised Z-tables and Z-reports that add non-standard columns. Date format `DD.MM.YYYY` is the SAP default in German locale; US locale uses `MM/DD/YYYY`.

### Sample data and why it looks the way it does

```csv
BELNR,BLDAT,BUKRS,WERKS,MATNR,TXZ01,MENGE,MEINS,LIFNR
4900012301,15.01.2024,1000,PLANT_MUM,MAT-DIESEL-001,Diesel Kraftstoff HSD,5400,L,1000234
4900013455,10.02.2024,1000,PLANT_DEL,MAT-DIESEL-001,Diesel Kraftstoff HSD,1638.07,gal,1000567
4900014001,05.03.2024,1000,PLANT_BLR,MAT-PETROL-001,Benzin RON92,3100,L,1000789
4900014222,28.01.2024,1000,PLANT_HYD,MAT-STEEL-001,Procurement Stahl,999999,INR,2000100
```

- German column headers (`BLDAT`, `MEINS`) reflect SAP's internal field names that often leak into exports
- Mixed units (L and gal) reflect real inconsistency between plants — one vendor invoices in gallons
- The INR procurement row represents a non-fuel purchase that needs Scope 3 categorisation
- The large INR value (999999) is intentionally flagged as an outlier to demonstrate the suspicious-row workflow
- `BUKRS` (company code) and `WERKS` (plant) are meaningful only with the client's master data — a realistic limitation

### What would break in real deployment

- Without the client's plant master, PLANT_MUM is opaque. Need a separate plant → location mapping upload.
- Material numbers (MATNR) are client-specific. Our keyword-based fuel detection (`diesel`, `kraftstoff`) would miss materials named numerically.
- Some SAP exports use tab-separated files with a `.txt` extension — the parser assumes comma-separated.
- Multi-currency SAP instances (EUR for procurement, INR for local fuel) would require exchange rate normalisation.
- Large exports (SE16N from MSEG for a full year) can be 100k+ rows — the parser needs streaming/chunked processing.

---

## Source 2: Utility Electricity

### Real-world format researched

- **PDF bills:** The most common format. Indian DISCOMs (BESCOM, BSES, MSEDCL) produce PDF bills with a fixed layout. Parsing requires template-based extraction or OCR — fragile at scale.
- **Portal CSV export:** Most DISCOM portals (e.g. BESCOM's self-service portal) allow CSV download of consumption history. Columns vary: some use `Consumption (kWh)`, others use `Units` (colloquial for kWh in India).
- **Green Button (US):** XML-based standard for utility data. Not widely available in India.
- **ESMI API (India):** Energy Smart Metering Infrastructure — emerging, not universally available.

**What I learned:** Billing periods almost never align to calendar months. A February bill might cover Jan 18 – Feb 17. This matters for carbon accounting because emissions need to be attributed to the correct reporting period. Meter IDs are the stable identifier across billing periods. Indian utilities often show consumption in "units" = kWh. Large commercial consumers may have separate demand charges (kVA) and energy charges (kWh); we only need kWh for Scope 2.

### Sample data and why it looks the way it does

```csv
meter_id,billing_period_start,billing_period_end,consumption_kwh,unit,site,supplier
MTR-BLR-001,2024-01-01,2024-01-31,48200,kWh,Bangalore HQ,BESCOM
MTR-BLR-001,2024-02-01,2024-02-29,51.3,MWh,Bangalore HQ,BESCOM
MTR-DEL-002,2024-03-01,2024-03-31,620000,kWh,Delhi Office,BSES
```

- `MTR-BLR-001` appears twice with different units (kWh vs MWh) — realistic when a portal changes its export format between months
- 620,000 kWh for Delhi in March is flagged as suspicious — realistic for a large data centre but should be verified
- `billing_period_start` is used as `activity_date`; `billing_period_end` is stored but not used in v1

### What would break in real deployment

- Billing period misalignment: if a bill covers parts of two months, we'd need to pro-rate consumption. Currently we assign all consumption to the period start month.
- Multiple tariff types on one bill (low-tension vs high-tension tariffs) produce multiple rows per meter per month — our current model creates one record per CSV row.
- PDF bills would require OCR. Different DISCOMs have completely different PDF layouts — no single parser works.
- For renewable energy certificates (RECs) or green tariffs, the Scope 2 location-based vs market-based distinction requires additional data fields.

---

## Source 3: Corporate Travel

### Real-world format researched

- **Concur (SAP) Expense API v4:** Returns JSON. `/api/v4.0/reports` for expense reports; individual line items include merchant, amount, date. Travel bookings via Concur Travel return itinerary data with segment type, carrier, origin, destination.
- **Navan (TripActions) API:** REST/JSON. `/v1/trips` returns bookings with `type` (air/hotel/car), dates, origin/destination IATA codes, and sometimes distance.
- **CSV exports:** Concur's "Expense Reports" export as CSV, but structured fields like airport codes become concatenated strings ("London Heathrow - New York JFK").

**What I learned:** Distance is not always provided — Concur often gives origin and destination city names or airport codes but not the route distance. IATA airport codes are the reliable identifier. Cabin class (economy, business, first) significantly affects emission factors (business class ≈ 2.9x economy per DEFRA). Hotel emission factors vary enormously by country and star rating. Ground transport (taxi, train, car rental) has different factors. Car rental in particular requires vehicle type data that is rarely in the booking record.

### Sample data and why it looks the way it does

```json
{"bookings": [
  {"type": "flight", "booking_ref": "BK-2024-001", "date": "2024-01-22", "origin": "BOM", "destination": "DEL", "carrier": "IndiGo"},
  {"type": "flight", "booking_ref": "BK-2024-002", "date": "2024-02-14", "origin": "SIN", "destination": "LHR", "carrier": "Singapore Airlines"},
  {"type": "flight", "booking_ref": "BK-2024-003", "date": "2024-03-07", "origin": "XYZ", "destination": "ABC", "carrier": "Unknown"},
  {"type": "hotel", "booking_ref": "BK-2024-004", "date": "2024-02-14", "city": "London", "hotel": "Marriott", "nights": 3},
  {"type": "ground_taxi", "booking_ref": "BK-2024-005", "date": "2024-01-22", "route": "Mumbai Airport-Office", "distance_km": 32, "vendor": "Uber"}
]}
```

- BOM→DEL and SIN→LHR are in our airport distance lookup (realistic common routes)
- XYZ→ABC is an intentionally unknown pair to demonstrate the flagging mechanism
- Hotel record shows nights (3) rather than distance — different quantity type
- `distance_km` is explicit in the taxi record — not always present; airport pair lookup is the fallback

### What would break in real deployment

- No cabin class → we use economy factors for all flights. Business travel is predominantly business/first class — this likely understates Scope 3 Category 6 by 2-3x.
- Our airport distance lookup has ~10 routes hardcoded. A real system needs the full IATA route database or a great-circle distance calculation library.
- Multi-leg flights (BOM→DXB→LHR) stored as a single booking would need to be split by leg for accurate distance calculation.
- Hotel emission factors vary by country (UK hotels ≈ 31 kg CO2e/night; US ≈ 37; India ≈ 15). We use a single UK average.
- Concur's actual API requires OAuth2 with the client's tenant URL — the JSON file upload is a simulation of that data shape.
