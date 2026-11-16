import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import Notification

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = int(self.scope['url_route']['kwargs']['user_id'])
        self.room_group_name = f'notifications_{self.user_id}'
        user = self.scope.get('user')
        if not user or not user.is_authenticated or user.id != self.user_id:
            await self.close()
            return
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data or '{}')
        except ValueError:
            return
        if data.get('type') == 'mark_read':
            await self.mark_notification_read(data.get('notification_id'))

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        updated = Notification.objects.filter(id=notification_id, recipient_id=self.user_id).update(read=True)
        if not updated:
            logger.warning('Notification %s not found for user %s.', notification_id, self.user_id)

    async def send_notification(self, event):
        await self.send(text_data=json.dumps(event['data']))
