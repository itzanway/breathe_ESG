from django.utils import timezone
from django.http import JsonResponse
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.response import Response
from rest_framework import status
from .models import Client, IngestionBatch, EmissionRecord, AuditLog
from .serializers import EmissionRecordSerializer, BatchSerializer, ClientSerializer
from .parsers import parse_sap, parse_utility, parse_travel
import traceback


def get_or_create_demo_client():
    client, _ = Client.objects.get_or_create(
        slug='demo',
        defaults={'name': 'Demo Enterprise Client'}
    )
    return client


@api_view(['GET'])
def health(request):
    return Response({'status': 'ok', 'message': 'Breathe ESG API running'})


@api_view(['GET', 'POST'])
def clients(request):
    if request.method == 'GET':
        return Response(ClientSerializer(Client.objects.all(), many=True).data)
    serializer = ClientSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@parser_classes([MultiPartParser])
def ingest_sap(request):
    return _ingest(request, 'sap')


@api_view(['POST'])
@parser_classes([MultiPartParser])
def ingest_utility(request):
    return _ingest(request, 'utility')


@api_view(['POST'])
@parser_classes([MultiPartParser])
def ingest_travel(request):
    return _ingest(request, 'travel')


def _ingest(request, source):
    client = get_or_create_demo_client()
    file_obj = request.FILES.get('file')
    if not file_obj:
        return Response({'error': 'No file uploaded'}, status=400)

    batch = IngestionBatch.objects.create(
        client=client,
        source=source,
        filename=file_obj.name,
        status=IngestionBatch.STATUS_PROCESSING,
    )

    try:
        content = file_obj.read().decode('utf-8', errors='replace')
        if source == 'sap':
            rows = parse_sap(content, client.id, batch.id)
        elif source == 'utility':
            rows = parse_utility(content, client.id, batch.id)
        elif source == 'travel':
            rows = parse_travel(content, client.id, batch.id)
        else:
            rows = []

        created = 0
        errors = 0
        for row in rows:
            try:
                EmissionRecord.objects.create(**row)
                created += 1
            except Exception:
                errors += 1

        batch.row_count = created
        batch.error_count = errors
        batch.status = IngestionBatch.STATUS_DONE
        batch.processed_at = timezone.now()
        batch.save()

        return Response({
            'batch_id': str(batch.id),
            'source': source,
            'rows_created': created,
            'rows_failed': errors,
            'status': 'done',
        })
    except Exception as e:
        batch.status = IngestionBatch.STATUS_FAILED
        batch.notes = traceback.format_exc()
        batch.save()
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
def records_list(request):
    qs = EmissionRecord.objects.select_related('client', 'batch').all()
    source = request.GET.get('source')
    scope = request.GET.get('scope')
    review_status = request.GET.get('review_status')
    client_slug = request.GET.get('client')

    if source:
        qs = qs.filter(batch__source=source)
    if scope:
        qs = qs.filter(scope=scope)
    if review_status:
        qs = qs.filter(review_status=review_status)
    if client_slug:
        qs = qs.filter(client__slug=client_slug)

    serializer = EmissionRecordSerializer(qs[:500], many=True)
    return Response({
        'count': qs.count(),
        'results': serializer.data,
    })


@api_view(['POST'])
def approve_record(request, record_id):
    try:
        record = EmissionRecord.objects.get(id=record_id)
    except EmissionRecord.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if record.is_locked:
        return Response({'error': 'Record is locked for audit'}, status=400)

    old_status = record.review_status
    record.review_status = EmissionRecord.STATUS_APPROVED
    record.reviewed_by = request.data.get('reviewer', 'analyst')
    record.reviewed_at = timezone.now()
    record.review_note = request.data.get('note', '')
    record.save()

    AuditLog.objects.create(
        record=record,
        action='approved',
        actor=record.reviewed_by,
        before={'review_status': old_status},
        after={'review_status': EmissionRecord.STATUS_APPROVED},
        note=record.review_note,
    )
    return Response({'status': 'approved', 'id': str(record.id)})


@api_view(['POST'])
def reject_record(request, record_id):
    try:
        record = EmissionRecord.objects.get(id=record_id)
    except EmissionRecord.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    if record.is_locked:
        return Response({'error': 'Record is locked for audit'}, status=400)

    old_status = record.review_status
    record.review_status = EmissionRecord.STATUS_REJECTED
    record.reviewed_by = request.data.get('reviewer', 'analyst')
    record.reviewed_at = timezone.now()
    record.review_note = request.data.get('note', '')
    record.save()

    AuditLog.objects.create(
        record=record,
        action='rejected',
        actor=record.reviewed_by,
        before={'review_status': old_status},
        after={'review_status': EmissionRecord.STATUS_REJECTED},
        note=record.review_note,
    )
    return Response({'status': 'rejected', 'id': str(record.id)})


@api_view(['POST'])
def lock_batch(request, batch_id):
    """Lock all approved records in a batch for audit. Irreversible."""
    try:
        batch = IngestionBatch.objects.get(id=batch_id)
    except IngestionBatch.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    locked = EmissionRecord.objects.filter(
        batch=batch, review_status=EmissionRecord.STATUS_APPROVED
    ).update(is_locked=True)

    return Response({'locked_count': locked, 'batch_id': str(batch_id)})


@api_view(['GET'])
def batches_list(request):
    batches = IngestionBatch.objects.select_related('client').order_by('-uploaded_at')[:50]
    return Response(BatchSerializer(batches, many=True).data)


@api_view(['GET'])
def summary(request):
    from django.db.models import Count, Sum
    total = EmissionRecord.objects.count()
    pending = EmissionRecord.objects.filter(review_status='pending').count()
    suspicious = EmissionRecord.objects.filter(review_status='suspicious').count()
    approved = EmissionRecord.objects.filter(review_status='approved').count()
    rejected = EmissionRecord.objects.filter(review_status='rejected').count()

    by_scope = {}
    for scope in [1, 2, 3]:
        by_scope[f'scope_{scope}'] = EmissionRecord.objects.filter(scope=scope).count()

    return Response({
        'total': total,
        'pending': pending,
        'suspicious': suspicious,
        'approved': approved,
        'rejected': rejected,
        'by_scope': by_scope,
    })
