from rest_framework import serializers
from .models import Client, IngestionBatch, EmissionRecord, AuditLog


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'


class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngestionBatch
        fields = '__all__'


class EmissionRecordSerializer(serializers.ModelSerializer):
    batch_source = serializers.CharField(source='batch.source', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)

    class Meta:
        model = EmissionRecord
        fields = '__all__'


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'
