import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async 
from ocpp.v16 import ChargePoint as OCPPChargePoint, call
from ocpp.v16.enums import Action, RegistrationStatus
from ocpp.routing import on
from django.utils import timezone
from .models import Charger, Transaction

class ChargerConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print(f"[WebSocket] Connection attempt from charge point: {self.scope['url_route']['kwargs']['charge_point_id']}")
        self.charge_point_id = self.scope["url_route"]["kwargs"]["charge_point_id"]
        self.charge_point = OCPPChargePoint(self.charge_point_id, self)
        
        # Create or update charger in database
        try:
            self.charger, _ = await self.get_or_create_charger()
            print(f"[WebSocket] Charger {self.charge_point_id} registered in database")
            await self.accept()
            print(f"[WebSocket] Connection accepted for charge point: {self.charge_point_id}")
            await self.charge_point.start()
            print(f"[WebSocket] OCPP protocol started for charge point: {self.charge_point_id}")
        except Exception as e:
            print(f"[WebSocket] Error during connection setup for {self.charge_point_id}: {str(e)}")
            raise

    async def disconnect(self, close_code):
        print(f"[WebSocket] Disconnection from charge point: {self.charge_point_id} with code: {close_code}")
        if hasattr(self, 'charger'):
            self.charger.status = 'Offline'
            await self.save_charger()
            print(f"[WebSocket] Charger {self.charge_point_id} marked as offline")
        else:
            print(f"[WebSocket] No charger instance found for {self.charge_point_id}")

    async def receive(self, text_data):
        print(f"[WebSocket] Received message from {self.charge_point_id}: {text_data}")
        try:
            await self.charge_point.route_message(text_data)
            print(f"[WebSocket] Message routed successfully for {self.charge_point_id}")
        except Exception as e:
            error_msg = str(e)
            print(f"[WebSocket] Error processing message from {self.charge_point_id}: {error_msg}")
            await self.send(text_data=json.dumps({
                'error': error_msg
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
            charger = await Charger.objects.aget(charger_id=self.charge_point_id)
            return charger, False
        except Charger.DoesNotExist:
            charger = await sync_to_async(Charger.objects.create)(
                charger_id=self.charge_point_id,
                status='connected'
            )
            return charger, True

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

    async def recv(self):
        """Receive messages from WebSocket."""
        try:
            # Use the channel layer's receive method
            message = await self.channel_layer.receive(self.channel_name)
            
            if message.get("type") == "websocket.receive":
                return message.get("text", "")
            elif message.get("type") == "websocket.disconnect":
                raise ConnectionError("WebSocket disconnected")
            
            return ""
            
        except AttributeError:
            # If no channel layer, fall back to basic receive
            message = await self.receive(text_data=None)
            return message if message else ""
        except Exception as e:
            print(f"[WebSocket] Error in recv: {str(e)}")
            raise

    async def send_message(self, message):
        """Send message to WebSocket."""
        try:
            if isinstance(message, str):
                await self.send(text_data=message)
            else:
                await self.send(text_data=json.dumps(message))
        except Exception as e:
            print(f"[WebSocket] Error in send_message: {str(e)}")
