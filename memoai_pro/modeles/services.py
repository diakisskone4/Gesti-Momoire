import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from projects.models import Chapter
from . import saspay
from .models import TemplatePurchase

logger = logging.getLogger(__name__)

# Une session SasPay en attente depuis moins de ce délai est réutilisée (évite les doubles paiements).
REUSE_PENDING_FOR = timedelta(minutes=30)
FINAL_SESSION_STATUSES = {'EXPIRED', 'CANCELLED', 'CANCELED'}


def reusable_pending_purchase(user, template):
    return (TemplatePurchase.objects
            .filter(user=user, template=template, status=TemplatePurchase.PENDING,
                    created_at__gte=timezone.now() - REUSE_PENDING_FOR)
            .exclude(checkout_url='')
            .first())


def refresh_purchase(purchase):
    """Interroge SasPay et met l'achat à jour. Ne se fie jamais au seul retour du navigateur :
    la session doit être payée ET la transaction vérifiée (statut, devise, montant)."""
    if purchase.status != TemplatePurchase.PENDING or not purchase.checkout_session_id:
        return purchase

    session = saspay.checkout_status(purchase.checkout_session_id)
    session_status = str(session.get('status') or '').upper()
    transaction_id = session.get('transaction_id') or ''

    if session_status in FINAL_SESSION_STATUSES:
        purchase.status = TemplatePurchase.CANCELLED
        purchase.save(update_fields=['status', 'updated_at'])
        return purchase

    if not transaction_id or str(session.get('transaction_status') or '').upper() != 'SUCCESS':
        # Paiement en cours ou échoué : le client peut encore réessayer sur la page SasPay.
        return purchase

    payment = saspay.verify_payment(transaction_id)
    amount = saspay.to_decimal(payment.get('requested_amount') or payment.get('amount'))
    if (str(payment.get('status') or '').upper() != 'SUCCESS'
            or (payment.get('currency') or purchase.currency) != purchase.currency
            or amount is None or amount < purchase.amount):
        logger.error('SasPay: paiement %s incohérent pour l\'achat %s : %s', transaction_id, purchase.id, payment)
        return purchase

    mark_paid(purchase, transaction_id, payment.get('reference') or session.get('transaction_reference') or '',
              saspay.to_decimal(payment.get('debited_amount')))
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
    try:
        from notifications.models import Notification
        Notification.objects.create(
            recipient=purchase.user, verb=f'Achat confirmé : modèle « {purchase.template.name} »',
            target_type='template', target_id=purchase.template_id,
            description='Vous pouvez maintenant l\'appliquer à vos mémoires.',
        )
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
