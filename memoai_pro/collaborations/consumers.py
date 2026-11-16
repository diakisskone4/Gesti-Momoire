import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from projects.access import can_read
from projects.models import Chapter, Project

logger = logging.getLogger(__name__)


class DocumentConsumer(AsyncWebsocketConsumer):
    """Édition en direct d'un mémoire : lecture pour l'encadrement, écriture pour l'auteur."""

    async def connect(self):
        self.project_id = int(self.scope['url_route']['kwargs']['project_id'])
        self.room_group_name = f'document_{self.project_id}'
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return
        access = await self.get_access(user)
        if access is None:
            await self.close()
            return
        self.can_write = access
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    @database_sync_to_async
    def get_access(self, user):
        """None : aucun accès ; False : lecture seule ; True : écriture."""
        project = Project.objects.filter(pk=self.project_id).first()
        if project is None or not can_read(project, user):
            return None
        return project.user_id == user.id

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data or '{}')
        except ValueError:
            return
        if data.get('type') != 'content_update' or not self.can_write:
            return
        chapter_id, content = data.get('chapter_id'), data.get('content')
        if not isinstance(content, str) or not await self.save_chapter_content(chapter_id, content):
            return
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'document_update',
            'data': {
                'type': 'content_update',
                'chapter_id': chapter_id,
                'content': content,
                'user': self.scope['user'].email,
            },
        })

    @database_sync_to_async
    def save_chapter_content(self, chapter_id, content):
        chapter = Chapter.objects.filter(id=chapter_id, project_id=self.project_id).first()
        if chapter is None:
            logger.warning('Chapter %s not found in project %s.', chapter_id, self.project_id)
            return False
        chapter.content = content
        chapter.save(update_fields=['content', 'updated_at'])
        return True

    async def document_update(self, event):
        await self.send(text_data=json.dumps(event['data']))
