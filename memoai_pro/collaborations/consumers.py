# collaborations/consumers.py
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from projects.models import Chapter

logger = logging.getLogger(__name__)

class DocumentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.room_group_name = f'document_{self.project_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        # Ex: mise à jour de contenu
        if data.get('type') == 'content_update':
            chapter_id = data.get('chapter_id')
            content = data.get('content')
            await self.save_chapter_content(chapter_id, content)
            # Diffuser aux autres
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'document_update',
                    'data': {
                        'type': 'content_update',
                        'chapter_id': chapter_id,
                        'content': content,
                        'user': self.scope['user'].email
                    }
                }
            )

    @database_sync_to_async
    def save_chapter_content(self, chapter_id, content):
        try:
            chapter = Chapter.objects.get(id=chapter_id)
            chapter.content = content
            chapter.save()
        except Chapter.DoesNotExist:
            logger.warning('Chapter %s not found while saving content.', chapter_id)

    async def document_update(self, event):
        await self.send(text_data=json.dumps(event['data']))