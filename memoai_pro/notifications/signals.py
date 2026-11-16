import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver

from collaborations.models import Comment, Validation
from .models import Notification

logger = logging.getLogger(__name__)


def push_notification(user_id, notif):
    """Envoi temps réel best-effort : si la couche Channels est indisponible, la
    notification reste enregistrée en base et sera lue au prochain chargement."""
    try:
        async_to_sync(get_channel_layer().group_send)(
            f'notifications_{user_id}',
            {
                'type': 'send_notification',
                'data': {
                    'id': notif.id,
                    'verb': notif.verb,
                    'description': notif.description,
                    'target_type': notif.target_type,
                    'target_id': notif.target_id,
                    'actor_name': notif.actor.full_name if notif.actor else None,
                    'read': notif.read,
                    'created_at': notif.created_at.isoformat(),
                },
            },
        )
    except Exception:
        logger.warning('Notification temps réel non envoyée (channel layer indisponible)', exc_info=True)


def notify(recipient, actor, verb, project, description=''):
    notif = Notification.objects.create(
        recipient=recipient, actor=actor, verb=verb,
        target_type='project', target_id=project.id, description=(description or '')[:100],
    )
    push_notification(recipient.id, notif)
    return notif


@receiver(post_save, sender=Comment)
def notify_comment(sender, instance, created, **kwargs):
    """Nouveau commentaire : prévenir l'auteur du mémoire et ses encadreurs (sauf l'auteur du commentaire)."""
    if not created or instance.parent_id is not None:
        return
    project = instance.project or (instance.chapter.project if instance.chapter_id else None)
    if project is None:
        return
    recipients = {project.user, project.supervisor, project.co_supervisor} - {None, instance.user}
    for user in recipients:
        notify(user, instance.user, 'a commenté', project, instance.content)


@receiver(post_save, sender=Validation)
def notify_validation(sender, instance, created, **kwargs):
    labels = {'APPROVED': 'a approuvé votre chapitre', 'REJECTED': 'a rejeté votre chapitre',
              'NEEDS_REVISION': 'demande une révision de votre chapitre'}
    if created and instance.status in labels:
        notify(instance.project.user, instance.validator, labels[instance.status], instance.project, instance.comment)
