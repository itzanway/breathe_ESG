"""
Parsers for each data source.
Each parser returns a list of dicts ready to become EmissionRecord rows.
Suspicious rows get a 'flags' list populated.
"""
import csv
import io
import json
from decimal import Decimal
from datetime import date, datetime


# ---------- unit normalisation ----------

LITRE_CONVERSIONS = {
    'l': 1, 'L': 1, 'litre': 1, 'litres': 1, 'liter': 1, 'liters': 1,
    'gal': Decimal('3.78541'), 'gallon': Decimal('3.78541'), 'gallons': Decimal('3.78541'),
    'gal_uk': Decimal('4.54609'),
    'm3': Decimal('1000'), 'cbm': Decimal('1000'),
}

KWH_CONVERSIONS = {
    'kwh': 1, 'kWh': 1, 'KWH': 1,
    'mwh': 1000, 'MWh': 1000, 'MWH': 1000,
    'gwh': 1000000, 'GWh': 1000000,
    'j': Decimal('0.000000277778'), 'kj': Decimal('0.000277778'), 'mj': Decimal('0.277778'),
}

KM_CONVERSIONS = {
    'km': 1, 'KM': 1,
    'mi': Decimal('1.60934'), 'mile': Decimal('1.60934'), 'miles': Decimal('1.60934'),
    'nm': Decimal('1.852'), 'nautical_mile': Decimal('1.852'),
}

# Approximate great-circle distances for common airport pairs (IATA → km)
AIRPORT_DISTANCES = {
    frozenset(['LHR', 'JFK']): 5540,
    frozenset(['BOM', 'DEL']): 1148,
    frozenset(['SIN', 'LHR']): 10841,
    frozenset(['LAX', 'JFK']): 3983,
    frozenset(['SYD', 'LAX']): 12051,
    frozenset(['DXB', 'LHR']): 5490,
    frozenset(['HKG', 'LHR']): 9638,
    frozenset(['CDG', 'JFK']): 5836,
    frozenset(['BLR', 'DEL']): 1740,
    frozenset(['MAA', 'DEL']): 2180,
    frozenset(['HYD', 'DEL']): 1492,
    frozenset(['CCU', 'DEL']): 1305,
}


def to_litres(value, unit):
    factor = LITRE_CONVERSIONS.get(unit.strip())
    if factor is None:
        return None, f"unknown_volume_unit:{unit}"
    return Decimal(str(value)) * Decimal(str(factor)), None


def to_kwh(value, unit):
    factor = KWH_CONVERSIONS.get(unit.strip())
    if factor is None:
        return None, f"unknown_energy_unit:{unit}"
    return Decimal(str(value)) * Decimal(str(factor)), None


def to_km(value, unit):
    factor = KM_CONVERSIONS.get(unit.strip())
    if factor is None:
        return None, f"unknown_distance_unit:{unit}"
    return Decimal(str(value)) * Decimal(str(factor)), None


def airport_distance_km(origin, dest):
    pair = frozenset([origin.upper().strip(), dest.upper().strip()])
    return AIRPORT_DISTANCES.get(pair)


def parse_date(raw):
    """Try multiple date formats common in SAP and utility exports."""
    for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%m/%d/%Y', '%Y%m%d', '%d-%b-%Y'):
        try:
            return datetime.strptime(str(raw).strip(), fmt).date()
        except ValueError:
            continue
    return None


# ---------- SAP flat-file parser ----------

SAP_COLUMN_MAP = {
    # English and German common column names -> our canonical names
    'BUKRS': 'company_code', 'Buchungskreis': 'company_code',
    'WERKS': 'plant', 'Werk': 'plant',
    'BLDAT': 'doc_date', 'Belegdatum': 'doc_date',
    'BELNR': 'doc_number', 'Belegnummer': 'doc_number',
    'MATNR': 'material', 'Material': 'material',
    'MENGE': 'quantity', 'Menge': 'quantity',
    'MEINS': 'unit', 'Mengeneinheit': 'unit',
    'LIFNR': 'vendor', 'Lieferant': 'vendor',
    'TXZ01': 'description', 'Kurztext': 'description',
    # Also accept already-English headers
    'company_code': 'company_code', 'plant': 'plant',
    'doc_date': 'doc_date', 'doc_number': 'doc_number',
    'material': 'material', 'quantity': 'quantity',
    'unit': 'unit', 'vendor': 'vendor', 'description': 'description',
}

FUEL_KEYWORDS = ['diesel', 'petrol', 'gasoline', 'fuel', 'kraftstoff', 'benzin', 'hsd', 'lng', 'cng', 'lpg']


def parse_sap(file_content, client_id, batch_id):
    rows = []
    reader = csv.DictReader(io.StringIO(file_content))
    for i, raw_row in enumerate(reader):
        # Normalise column names
        row = {SAP_COLUMN_MAP.get(k.strip(), k.strip()): v.strip() for k, v in raw_row.items()}

        flags = []
        activity_date = parse_date(row.get('doc_date', ''))
        if not activity_date:
            flags.append('unparseable_date')
            activity_date = date.today()

        raw_qty_str = row.get('quantity', '0').replace(',', '.')
        try:
            raw_qty = Decimal(raw_qty_str)
        except Exception:
            raw_qty = Decimal('0')
            flags.append('unparseable_quantity')

        raw_unit = row.get('unit', 'L')
        description = (row.get('description', '') + ' ' + row.get('material', '')).lower()
        is_fuel = any(kw in description for kw in FUEL_KEYWORDS)

        if is_fuel:
            norm_qty, err = to_litres(raw_qty, raw_unit)
            if err:
                flags.append(err)
                norm_qty = raw_qty
            norm_unit = 'litres'
            category = 'fuel_' + next((kw for kw in FUEL_KEYWORDS if kw in description), 'other')
            scope = 1
        else:
            # Procurement — Scope 3 by default
            norm_qty = raw_qty
            norm_unit = raw_unit
            category = 'procurement'
            scope = 3

        if norm_qty and norm_qty > 100000:
            flags.append('outlier_high_value')
        if norm_qty and norm_qty <= 0:
            flags.append('zero_or_negative')

        rows.append({
            'client_id': client_id,
            'batch_id': batch_id,
            'scope': scope,
            'category': category,
            'activity_date': activity_date,
            'quantity': norm_qty or Decimal('0'),
            'unit': norm_unit,
            'raw_quantity': raw_qty,
            'raw_unit': raw_unit,
            'source_ref': row.get('doc_number', ''),
            'location': row.get('plant', ''),
            'vendor': row.get('vendor', ''),
            'review_status': 'suspicious' if flags else 'pending',
            'flags': flags,
        })
    return rows


# ---------- Utility CSV parser ----------

def parse_utility(file_content, client_id, batch_id):
    rows = []
    reader = csv.DictReader(io.StringIO(file_content))
    for raw_row in reader:
        row = {k.strip().lower(): v.strip() for k, v in raw_row.items()}
        flags = []

        # Try multiple common column name patterns
        date_val = row.get('billing_period_start') or row.get('date') or row.get('period_start') or row.get('month') or ''
        activity_date = parse_date(date_val)
        if not activity_date:
            flags.append('unparseable_date')
            activity_date = date.today()

        raw_qty_str = (row.get('consumption_kwh') or row.get('kwh') or row.get('usage') or row.get('quantity') or '0').replace(',', '')
        try:
            raw_qty = Decimal(raw_qty_str)
        except Exception:
            raw_qty = Decimal('0')
            flags.append('unparseable_quantity')

        raw_unit = row.get('unit') or 'kWh'
        norm_qty, err = to_kwh(raw_qty, raw_unit)
        if err:
            flags.append(err)
            norm_qty = raw_qty

        meter_id = row.get('meter_id') or row.get('meter') or row.get('account_number') or ''
        site = row.get('site') or row.get('location') or row.get('facility') or ''

        if norm_qty and norm_qty > 500000:
            flags.append('outlier_high_kwh')
        if norm_qty and norm_qty <= 0:
            flags.append('zero_or_negative')

        rows.append({
            'client_id': client_id,
            'batch_id': batch_id,
            'scope': 2,
            'category': 'electricity',
            'activity_date': activity_date,
            'quantity': norm_qty or Decimal('0'),
            'unit': 'kWh',
            'raw_quantity': raw_qty,
            'raw_unit': raw_unit,
            'source_ref': meter_id,
            'location': site,
            'vendor': row.get('supplier') or row.get('utility') or '',
            'review_status': 'suspicious' if flags else 'pending',
            'flags': flags,
        })
    return rows


# ---------- Travel JSON parser ----------

FLIGHT_EMISSION_FACTOR_PER_KM = Decimal('0.255')   # kg CO2e per passenger-km (DEFRA 2023 economy)
HOTEL_EMISSION_FACTOR_PER_NIGHT = Decimal('31.2')  # kg CO2e per night (UK average)
GROUND_EMISSION_FACTOR_PER_KM = Decimal('0.192')   # kg CO2e per km (taxi/car)


def parse_travel(file_content, client_id, batch_id):
    rows = []
    try:
        data = json.loads(file_content)
    except json.JSONDecodeError:
        return []

    bookings = data if isinstance(data, list) else data.get('bookings', data.get('trips', []))

    for booking in bookings:
        flags = []
        btype = booking.get('type', '').lower()
        activity_date = parse_date(booking.get('date') or booking.get('departure_date') or booking.get('check_in') or '')
        if not activity_date:
            flags.append('unparseable_date')
            activity_date = date.today()

        if btype in ('flight', 'air', 'air_travel'):
            origin = booking.get('origin') or booking.get('from') or ''
            dest = booking.get('destination') or booking.get('to') or ''
            dist_km = booking.get('distance_km')
            if dist_km:
                norm_qty = Decimal(str(dist_km))
                norm_unit = 'km'
            elif origin and dest:
                dist_km = airport_distance_km(origin, dest)
                if dist_km:
                    norm_qty = Decimal(str(dist_km))
                    norm_unit = 'km'
                else:
                    norm_qty = Decimal('0')
                    norm_unit = 'km'
                    flags.append(f'unknown_airport_pair:{origin}-{dest}')
            else:
                norm_qty = Decimal('0')
                norm_unit = 'km'
                flags.append('missing_route')
            category = 'air_travel'
            location = f"{origin}-{dest}"

        elif btype in ('hotel', 'accommodation'):
            nights = booking.get('nights') or booking.get('duration_nights') or 1
            norm_qty = Decimal(str(nights))
            norm_unit = 'nights'
            category = 'hotel'
            location = booking.get('city') or booking.get('hotel') or ''

        elif btype in ('ground', 'car', 'taxi', 'rail', 'train'):
            dist = booking.get('distance_km') or booking.get('distance') or 0
            raw_unit = booking.get('unit') or 'km'
            norm_qty, err = to_km(Decimal(str(dist)), raw_unit)
            if err:
                flags.append(err)
                norm_qty = Decimal(str(dist))
            norm_unit = 'km'
            category = f"ground_{btype}"
            location = booking.get('route') or ''
        else:
            flags.append(f'unknown_travel_type:{btype}')
            norm_qty = Decimal('0')
            norm_unit = 'unknown'
            category = 'unknown_travel'
            location = ''

        rows.append({
            'client_id': client_id,
            'batch_id': batch_id,
            'scope': 3,
            'category': category,
            'activity_date': activity_date,
            'quantity': norm_qty,
            'unit': norm_unit,
            'raw_quantity': norm_qty,
            'raw_unit': norm_unit,
            'source_ref': booking.get('booking_ref') or booking.get('id') or '',
            'location': location,
            'vendor': booking.get('carrier') or booking.get('airline') or booking.get('hotel') or '',
            'review_status': 'suspicious' if flags else 'pending',
            'flags': flags,
        })
    return rows
