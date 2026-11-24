import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from projects.models import Chapter
from . import jemeni
from .models import TemplatePurchase

logger = logging.getLogger(__name__)

# Une page de paiement Jɛmɛnipay expire au bout de 30 minutes.
CHECKOUT_LIFETIME = timedelta(minutes=30)
# En dessous de ce délai, la page existante est réutilisée (évite les doubles paiements).
REUSE_PENDING_FOR = timedelta(minutes=25)
# Sans confirmation au-delà de ce délai, l'achat est considéré comme abandonné.
ABANDONED_AFTER = timedelta(hours=2)


def is_payable(purchase):
    return (jemeni.is_enabled() and purchase.status == TemplatePurchase.PENDING and bool(purchase.checkout_url)
            and purchase.provider == jemeni.provider()
            and purchase.created_at >= timezone.now() - CHECKOUT_LIFETIME)


def reusable_pending_purchase(user, template):
    if not jemeni.is_enabled():
        return None
    return (TemplatePurchase.objects
            .filter(user=user, template=template, status=TemplatePurchase.PENDING, provider=jemeni.provider(),
                    created_at__gte=timezone.now() - REUSE_PENDING_FOR)
            .exclude(checkout_url='')
            .first())


def refresh_purchase(purchase):
    """Interroge Jɛmɛnipay et met l'achat à jour. Ne se fie jamais au seul retour du navigateur ni au
    contenu du webhook : la transaction doit être à l'état « payé », pour le bon montant.
    Un achat annulé ou échoué reste vérifiable : un paiement confirmé tardivement est toujours enregistré."""
    if purchase.status == TemplatePurchase.PAID or not purchase.checkout_session_id:
        return purchase
    if not jemeni.is_enabled() or purchase.provider != jemeni.provider():
        return purchase  # ancien achat SasPay, ou fait avec l'autre jeu de clés (test / réel)

    payment = jemeni.get_payment(purchase.checkout_session_id)
    if str(payment.get('id') or '') != purchase.checkout_session_id:
        logger.error("Jemeni: transaction inattendue pour l'achat %s : %s", purchase.id, str(payment)[:300])
        return purchase
    state = jemeni.to_state(payment.get('state'))

    if state == jemeni.STATE_COMPLETED:
        amount = jemeni.to_decimal(payment.get('amount'))
        if amount is None or amount < purchase.amount:
            logger.error("Jemeni: montant incohérent pour l'achat %s : %s", purchase.id, str(payment)[:300])
            return purchase
        mark_paid(purchase, purchase.checkout_session_id,
                  str(payment.get('reference') or purchase.transaction_reference), amount)
        return purchase

    if purchase.status == TemplatePurchase.PENDING:
        if state in jemeni.STATES_FAILED:
            purchase.status = TemplatePurchase.FAILED
            purchase.save(update_fields=['status', 'updated_at'])
        elif purchase.created_at < timezone.now() - ABANDONED_AFTER:
            purchase.status = TemplatePurchase.CANCELLED
            purchase.save(update_fields=['status', 'updated_at'])
    return purchase


def mark_paid(purchase, transaction_id, reference, charged=None):
    with transaction.atomic():
        locked = TemplatePurchase.objects.select_for_update().get(pk=purchase.pk)
        if locked.status == TemplatePurchase.PAID:
            purchase.refresh_from_db()
            return
        locked.status = TemplatePurchase.PAID
        locked.transaction_id = transaction_id
        locked.transaction_reference = reference
        locked.amount_charged = charged
        locked.paid_at = timezone.now()
        locked.save()
    purchase.refresh_from_db()
    notify_buyer(purchase, f'Achat confirmé : modèle « {purchase.template.name} »',
                 'Vous pouvez maintenant l\'appliquer à vos mémoires.')


def notify_buyer(purchase, verb, description):
    try:
        from notifications.models import Notification
        with transaction.atomic():
            Notification.objects.create(recipient=purchase.user, verb=verb[:100], target_type='template',
                                        target_id=purchase.template_id, description=description)
    except Exception:  # la notification ne doit jamais bloquer la confirmation du paiement
        logger.warning('Notification d\'achat non créée', exc_info=True)


def apply_template(template, project):
    """Ajoute le plan du modèle (chapitres + sections, avec conseils) à la suite des chapitres existants."""
    with transaction.atomic():
        start = (Chapter.objects.filter(project=project, parent=None)
                 .order_by('-order').values_list('order', flat=True).first() or 0)
        created = 0
        for index, entry in enumerate(template.structure, start=1):
            chapter = Chapter.objects.create(
                project=project, title=entry['title'][:255], order=start + index,
                type=entry.get('type', 'chapter'),
                content=f"[Conseil du modèle : {entry.get('guidance', '')}]\n\n" if entry.get('guidance') else '',
            )
            created += 1
            for s_index, section in enumerate(entry.get('sections', []), start=1):
                Chapter.objects.create(
                    project=project, parent=chapter, title=section['title'][:255], order=s_index, type='section',
                    content=f"[Conseil du modèle : {section.get('guidance', '')}]\n\n" if section.get('guidance') else '',
                )
                created += 1
        project.template = template
        fields = ['template', 'updated_at']
        if project.status == 'DRAFT':
            project.status = 'IN_PROGRESS'
            fields.append('status')
        project.save(update_fields=fields)
    return created
