from rest_framework import serializers
from ..models import Charger, Transaction

class ChargerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Charger
        fields = ['id', 'status', 'last_heartbeat', 'vendor', 'model', 
                 'serial_number', 'firmware_version', 'created_at', 'updated_at']
        read_only_fields = fields

class TransactionSerializer(serializers.ModelSerializer):
    charger_id = serializers.CharField(source='charger.id')
    
    class Meta:
        model = Transaction
        fields = ['id', 'charger_id', 'id_tag', 'start_time', 'stop_time',
                 'meter_start', 'meter_stop', 'reason', 'created_at', 'updated_at']
        read_only_fields = fields