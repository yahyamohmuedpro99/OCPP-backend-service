from djongo import models
from django.utils import timezone

class Charger(models.Model):
    charger_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=50, default='disconnected')
    last_heartbeat = models.DateTimeField(null=True)
    meter_value = models.FloatField(default=0.0)
    vendor = models.CharField(max_length=100, null=True, blank=True)
    model = models.CharField(max_length=100, null=True, blank=True)
    serial_number = models.CharField(max_length=100, null=True, blank=True)
    firmware_version = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = False  
        db_table = 'chargers'

    def update_heartbeat(self):
        self.last_heartbeat = timezone.now()
        self.save()

class Transaction(models.Model):
    id = models.AutoField(primary_key=True)
    charger = models.ForeignKey(Charger, on_delete=models.CASCADE, related_name='transactions')
    id_tag = models.CharField(max_length=20)
    start_time = models.DateTimeField()
    stop_time = models.DateTimeField(null=True)
    meter_start = models.IntegerField()
    meter_stop = models.IntegerField(null=True)
    reason = models.CharField(max_length=50, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Transaction {self.id} - Charger {self.charger.id}'

    def stop_transaction(self, meter_stop, stop_time=None, reason=None):
        self.meter_stop = meter_stop
        self.stop_time = stop_time or timezone.now()
        self.reason = reason
        self.save()
