from django.db import models
import uuid


class Client(models.Model):
    """
    Multi-tenancy: every data row belongs to a client.
    In a real deployment you'd tie this to auth users/orgs.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class IngestionBatch(models.Model):
    """
    Tracks a single upload event (one file = one batch).
    Source-of-truth: we always know which file produced which rows.
    """
    SOURCE_SAP = 'sap'
    SOURCE_UTILITY = 'utility'
    SOURCE_TRAVEL = 'travel'
    SOURCE_CHOICES = [
        (SOURCE_SAP, 'SAP Fuel & Procurement'),
        (SOURCE_UTILITY, 'Utility Electricity'),
        (SOURCE_TRAVEL, 'Corporate Travel'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_DONE = 'done'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_DONE, 'Done'),
        (STATUS_FAILED, 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='batches')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    filename = models.CharField(max_length=500)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    row_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.client} / {self.source} / {self.uploaded_at:%Y-%m-%d}"


class EmissionRecord(models.Model):
    """
    The canonical normalized row. One record = one activity entry.
    All quantities stored in SI base units after normalization.
    Scope 1/2/3 per GHG Protocol.
    """
    SCOPE_1 = 1  # Direct emissions (fuel combustion)
    SCOPE_2 = 2  # Purchased electricity
    SCOPE_3 = 3  # Value chain (travel, procurement)
    SCOPE_CHOICES = [(1, 'Scope 1'), (2, 'Scope 2'), (3, 'Scope 3')]

    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_SUSPICIOUS = 'suspicious'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending review'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_SUSPICIOUS, 'Flagged suspicious'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='records')
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='records')

    # Scope & category
    scope = models.IntegerField(choices=SCOPE_CHOICES)
    category = models.CharField(max_length=100)  # e.g. "fuel_diesel", "electricity", "air_travel"

    # Activity data (normalized)
    activity_date = models.DateField()
    quantity = models.DecimalField(max_digits=18, decimal_places=6)
    unit = models.CharField(max_length=50)          # always the normalized unit (litres, kWh, km)
    raw_quantity = models.DecimalField(max_digits=18, decimal_places=6)
    raw_unit = models.CharField(max_length=50)      # original unit before normalization

    # Source metadata (varies by source type)
    source_ref = models.CharField(max_length=255, blank=True)   # SAP doc num, meter id, booking ref
    location = models.CharField(max_length=255, blank=True)     # plant code, site, airport pair
    vendor = models.CharField(max_length=255, blank=True)

    # Review workflow
    review_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    reviewed_by = models.CharField(max_length=255, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)

    # Audit trail — immutable once approved
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Suspicion flags (set during ingestion)
    flags = models.JSONField(default=list)  # list of strings e.g. ["unit_mismatch","outlier_value"]

    class Meta:
        ordering = ['-activity_date']

    def __str__(self):
        return f"{self.client} / {self.category} / {self.activity_date}"


class AuditLog(models.Model):
    """
    Immutable log of every change to an EmissionRecord.
    Required for auditor sign-off.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.ForeignKey(EmissionRecord, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=100)   # e.g. "approved", "edited", "flagged"
    actor = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['timestamp']
