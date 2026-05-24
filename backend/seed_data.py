"""
Run with: python3 manage.py shell < seed_data.py
Creates realistic sample data for all three source types.
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from ingestion.models import Client, IngestionBatch, EmissionRecord
from datetime import date
from decimal import Decimal
import uuid

client, _ = Client.objects.get_or_create(slug='demo', defaults={'name': 'Demo Enterprise Client'})

# --- SAP batch ---
sap_batch = IngestionBatch.objects.create(
    client=client, source='sap', filename='GR55_fuel_Q1_2024.csv',
    status='done', row_count=4, error_count=0
)
sap_rows = [
    dict(scope=1, category='fuel_diesel', activity_date=date(2024,1,15),
         quantity=Decimal('5400'), unit='litres', raw_quantity=Decimal('5400'), raw_unit='L',
         source_ref='4900012301', location='PLANT_MUM', vendor='HPCL', flags=[]),
    dict(scope=1, category='fuel_diesel', activity_date=date(2024,2,10),
         quantity=Decimal('6200'), unit='litres', raw_quantity=Decimal('1638.07'), raw_unit='gal',
         source_ref='4900013455', location='PLANT_DEL', vendor='BPCL', flags=['unit_converted_from_gal']),
    dict(scope=1, category='fuel_petrol', activity_date=date(2024,3,5),
         quantity=Decimal('3100'), unit='litres', raw_quantity=Decimal('3100'), raw_unit='L',
         source_ref='4900014001', location='PLANT_BLR', vendor='IOC', flags=[]),
    dict(scope=3, category='procurement', activity_date=date(2024,1,28),
         quantity=Decimal('999999'), unit='INR', raw_quantity=Decimal('999999'), raw_unit='INR',
         source_ref='4900014222', location='PLANT_HYD', vendor='Tata Steel',
         flags=['outlier_high_value', 'procurement_not_yet_categorised']),
]
for r in sap_rows:
    EmissionRecord.objects.create(client=client, batch=sap_batch,
        review_status='suspicious' if r['flags'] else 'pending', **r)

# --- Utility batch ---
util_batch = IngestionBatch.objects.create(
    client=client, source='utility', filename='BESCOM_Q1_2024.csv',
    status='done', row_count=3, error_count=0
)
util_rows = [
    dict(scope=2, category='electricity', activity_date=date(2024,1,1),
         quantity=Decimal('48200'), unit='kWh', raw_quantity=Decimal('48200'), raw_unit='kWh',
         source_ref='MTR-BLR-001', location='Bangalore HQ', vendor='BESCOM', flags=[]),
    dict(scope=2, category='electricity', activity_date=date(2024,2,1),
         quantity=Decimal('51300'), unit='kWh', raw_quantity=Decimal('51.3'), raw_unit='MWh',
         source_ref='MTR-BLR-001', location='Bangalore HQ', vendor='BESCOM', flags=['unit_converted_from_MWh']),
    dict(scope=2, category='electricity', activity_date=date(2024,3,1),
         quantity=Decimal('620000'), unit='kWh', raw_quantity=Decimal('620000'), raw_unit='kWh',
         source_ref='MTR-DEL-002', location='Delhi Office', vendor='BSES',
         flags=['outlier_high_kwh']),
]
for r in util_rows:
    EmissionRecord.objects.create(client=client, batch=util_batch,
        review_status='suspicious' if r['flags'] else 'pending', **r)

# --- Travel batch ---
travel_batch = IngestionBatch.objects.create(
    client=client, source='travel', filename='concur_trips_Q1_2024.json',
    status='done', row_count=5, error_count=0
)
travel_rows = [
    dict(scope=3, category='air_travel', activity_date=date(2024,1,22),
         quantity=Decimal('1148'), unit='km', raw_quantity=Decimal('1148'), raw_unit='km',
         source_ref='BK-2024-001', location='BOM-DEL', vendor='IndiGo', flags=[]),
    dict(scope=3, category='air_travel', activity_date=date(2024,2,14),
         quantity=Decimal('10841'), unit='km', raw_quantity=Decimal('10841'), raw_unit='km',
         source_ref='BK-2024-002', location='SIN-LHR', vendor='Singapore Airlines', flags=[]),
    dict(scope=3, category='air_travel', activity_date=date(2024,3,7),
         quantity=Decimal('0'), unit='km', raw_quantity=Decimal('0'), raw_unit='km',
         source_ref='BK-2024-003', location='XYZ-ABC',
         flags=['unknown_airport_pair:XYZ-ABC']),
    dict(scope=3, category='hotel', activity_date=date(2024,2,14),
         quantity=Decimal('3'), unit='nights', raw_quantity=Decimal('3'), raw_unit='nights',
         source_ref='BK-2024-004', location='London', vendor='Marriott', flags=[]),
    dict(scope=3, category='ground_taxi', activity_date=date(2024,1,22),
         quantity=Decimal('32'), unit='km', raw_quantity=Decimal('32'), raw_unit='km',
         source_ref='BK-2024-005', location='Mumbai Airport-Office', vendor='Uber', flags=[]),
]
for r in travel_rows:
    EmissionRecord.objects.create(client=client, batch=travel_batch,
        review_status='suspicious' if r['flags'] else 'pending', **r)

print(f"Seeded: {EmissionRecord.objects.count()} records across 3 batches")
