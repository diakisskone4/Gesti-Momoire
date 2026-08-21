# notifications/signals.py
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification
from collaborations.models import Comment, Validation
from projects.models import Project

@receiver(post_save, sender=Comment)
def notify_comment(sender, instance, created, **kwargs):
    if created and instance.parent is None:
        # Notifier l'encadreur ou l'étudiant
        recipients = []
        project = instance.project
        if project:
            if instance.user != project.user:
                recipients.append(project.user)
            if project.supervisor and instance.user != project.supervisor:
                recipients.append(project.supervisor)
        for user in recipients:
            notif = Notification.objects.create(
                recipient=user,
                actor=instance.user,
                verb='a commenté',
                target_type='project',
                target_id=instance.project.id,
                description=instance.content[:100]
            )
            # Envoyer en temps réel via WebSocket
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'notifications_{user.id}',
                {
                    'type': 'send_notification',
                    'data': {
                        'id': notif.id,
                        'verb': notif.verb,
                        'description': notif.description,
                        'created_at': notif.created_at.isoformat()
                    }
                }
            )

@receiver(post_save, sender=Validation)
def notify_validation(sender, instance, created, **kwargs):
    if created and instance.status in ['APPROVED', 'REJECTED']:
        notif = Notification.objects.create(
            recipient=instance.project.user,
            actor=instance.validator,
            verb=f'a {instance.status.lower()} votre chapitre',
            target_type='project',
            target_id=instance.project.id,
            description=instance.comment[:100]
        )
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'notifications_{instance.project.user.id}',
            {
                'type': 'send_notification',
                'data': {
                    'id': notif.id,
                    'verb': notif.verb,
                    'description': notif.description,
                    'created_at': notif.created_at.isoformat()
                }
            }
        )