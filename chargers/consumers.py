import json
from channels.generic.websocket import AsyncWebsocketConsumer
from ocpp.v16 import ChargePoint as OCPPChargePoint, call
from ocpp.v16.enums import Action, RegistrationStatus
from ocpp.routing import on
from django.utils import timezone
from .models import Charger, Transaction

class ChargerConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.charge_point_id = self.scope["url_route"]["kwargs"]["charge_point_id"]
        self.charge_point = OCPPChargePoint(self.charge_point_id, self)
        
        # Create or update charger in database
        self.charger, _ = await self.get_or_create_charger()
        await self.accept()
        await self.charge_point.start()

    async def disconnect(self, close_code):
        if hasattr(self, 'charger'):
            self.charger.status = 'Offline'
            await self.save_charger()

    async def receive(self, text_data):
        try:
            await self.charge_point.route_message(text_data)
        except Exception as e:
            await self.send(text_data=json.dumps({
                'error': str(e)
            }))

    @on(Action.BootNotification)
    async def on_boot_notification(self, charge_point_model, charge_point_vendor, **kwargs):
        self.charger.model = charge_point_model
        self.charger.vendor = charge_point_vendor
        self.charger.firmware_version = kwargs.get('firmware_version')
        self.charger.serial_number = kwargs.get('charge_point_serial_number')
        await self.save_charger()

        return call.BootNotificationPayload(
            current_time=timezone.now().isoformat(),
            interval=300,
            status=RegistrationStatus.accepted
        )

    @on(Action.Heartbeat)
    async def on_heartbeat(self):
        await self.charger.update_heartbeat()
        return call.HeartbeatPayload(
            current_time=timezone.now().isoformat()
        )

    @on(Action.StartTransaction)
    async def on_start_transaction(self, id_tag, meter_start, **kwargs):
        transaction = Transaction(
            charger=self.charger,
            id_tag=id_tag,
            meter_start=meter_start,
            start_time=timezone.now()
        )
        await self.save_transaction(transaction)
        
        self.charger.status = 'Charging'
        await self.save_charger()

        return call.StartTransactionPayload(
            transaction_id=transaction.id,
            id_tag_info={'status': 'Accepted'}
        )

    @on(Action.StopTransaction)
    async def on_stop_transaction(self, meter_stop, transaction_id, **kwargs):
        transaction = await self.get_transaction(transaction_id)
        if transaction:
            await transaction.stop_transaction(
                meter_stop=meter_stop,
                reason=kwargs.get('reason')
            )

        self.charger.status = 'Available'
        await self.save_charger()

        return call.StopTransactionPayload(
            id_tag_info={'status': 'Accepted'}
        )

    @on(Action.Authorize)
    async def on_authorize(self, id_tag):
        # In a real implementation, you would check the id_tag against a database
        return call.AuthorizePayload(
            id_tag_info={'status': 'Accepted'}
        )

    async def get_or_create_charger(self):
        try:
            charger = await Charger.objects.aget(id=self.charge_point_id)
        except Charger.DoesNotExist:
            charger = Charger(id=self.charge_point_id)
        charger.status = 'Available'
        await self.save_charger(charger)
        return charger, False

    async def save_charger(self, charger=None):
        if charger is None:
            charger = self.charger
        await charger.asave()

    async def get_transaction(self, transaction_id):
        try:
            return await Transaction.objects.aget(id=transaction_id)
        except Transaction.DoesNotExist:
            return None

    async def save_transaction(self, transaction):
        await transaction.asave()
