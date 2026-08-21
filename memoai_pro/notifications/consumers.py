import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Notification

logger = logging.getLogger(__name__)

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f'notifications_{self.user_id}'

        if self.scope['user'].id != int(self.user_id):
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        # Marquer comme lu
        data = json.loads(text_data)
        if data.get('type') == 'mark_read':
            notification_id = data.get('notification_id')
            await self.mark_notification_read(notification_id)

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        try:
            notif = Notification.objects.get(id=notification_id, recipient_id=self.user_id)
            notif.read = True
            notif.save()
        except Notification.DoesNotExist:
            logger.warning('Notification %s not found for user %s.', notification_id, self.user_id)

    async def send_notification(self, event):
        await self.send(text_data=json.dumps(event['data']))