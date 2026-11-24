"""API de paiement de MemoAI : encaissement direct par Orange Money, Moov Money et Wave.

1. Le client choisit son opérateur et envoie l'argent au numéro d'encaissement affiché (PAYMENT_NUMBER, PAYMENT_NUMBER_MOOV...).
2. Il déclare son numéro et la référence de la transaction (reçue par SMS ou dans son application).
3. Le paiement est confirmé :
   - automatiquement, quand le téléphone d'encaissement (application « MemoAI Encaissement ») transmet le
     message de l'opérateur et que référence, montant, opérateur et numéro concordent ;
   - sinon par un administrateur, qui vérifie sur son compte mobile money.

Le client ne peut jamais confirmer lui-même un paiement : sa déclaration n'est qu'une demande de vérification.
La lecture des messages est volontairement prudente : au moindre doute, l'achat reste « en vérification ».
"""
import hashlib
import logging
import re
import secrets
import unicodedata
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from users.models import User
from users.password_reset import email_configured
from . import services
from .models import PaymentDevice, PaymentMessage, TemplatePurchase

logger = logging.getLogger(__name__)

PROVIDER = TemplatePurchase.PROVIDER_MOBILE_MONEY
OPERATORS = {
    'orange': {'label': 'Orange Money', 'ussd': '#144#',
               'steps': "Composez #144# (ou ouvrez votre application Orange Money), puis choisissez le transfert d'argent."},
    'moov': {'label': 'Moov Money', 'ussd': '*166#',
             'steps': "Composez *166# (ou ouvrez votre application Moov Money), puis choisissez le transfert d'argent."},
    'wave': {'label': 'Wave', 'ussd': '',
             'steps': "Ouvrez l'application Wave, puis touchez « Envoyer »."},
}
# Le message doit être arrivé après l'ouverture de l'achat (tolérance : horloges décalées).
CLOCK_TOLERANCE = timedelta(minutes=5)
KEEP_UNMATCHED_FOR = timedelta(days=90)


class PaymentError(Exception):
    pass


# ---------------------------------------------------------------- configuration

def local_number(operator):
    """Numéro qui encaisse pour cet opérateur, sur 8 chiffres (sans l'indicatif) ; '' s'il n'est pas configuré."""
    return clean_phone(settings.PAYMENT_NUMBERS.get(operator)) or clean_phone(settings.PAYMENT_NUMBER)


def local_numbers():
    return {local_number(operator) for operator in OPERATORS} - {''}


def is_enabled():
    return bool(clean_phone(settings.PAYMENT_NUMBER))


def options():
    operators = []
    for code, info in OPERATORS.items():
        number = local_number(code)
        operators.append({'code': code, **info, 'number': number,
                          'number_display': ' '.join(number[i:i + 2] for i in range(0, 8, 2))})
    return {'holder': settings.PAYMENT_HOLDER, 'operators': operators}


# ---------------------------------------------------------------- normalisation

def clean_phone(value):
    """« +223 76 12 34 56 » → « 76123456 » ; '' si ce n'est pas un numéro malien."""
    digits = re.sub(r'\D', '', str(value or ''))
    digits = re.sub(r'^(00)?223(?=\d{8}$)', '', digits)
    return digits if re.fullmatch(r'\d{8}', digits) else ''


def clean_reference(value):
    """Référence comparée sans espaces, ponctuation ni casse."""
    return re.sub(r'[^A-Z0-9]', '', str(value or '').upper())


def is_reference(ref):
    """Vrai si la chaîne peut identifier une transaction : jamais un numéro, une date, une heure ou un montant."""
    if not 6 <= len(ref) <= 40 or sum(c.isdigit() for c in ref) < 4:
        return False
    if re.fullmatch(r'\d+(F|FCFA|CFA|XOF)?|(F|FCFA|CFA|XOF)\d+', ref):
        return ref.isdigit() and len(ref) >= 9 and not re.fullmatch(r'(00)?223\d{8}', ref)
    return True


def _plain(text):
    text = unicodedata.normalize('NFKD', str(text or ''))
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', text).strip()


# ---------------------------------------------------------------- lecture d'un message d'opérateur

_CREDIT = re.compile(r'\b(recu|recue|credite|received)\b')
_OUTGOING = re.compile(r'\b(envoye|envoyee|transfere|transferee|paye|payee|retire|retrait|debite|achat|sent|paid|'
                       r'echoue|annule|annulee)\b|\brecue? par\b')
_NUMBER = r'(?:\d{1,3}(?:[ .,]\d{3})+|\d+)(?:[.,]\d{1,2})?'
_AMOUNT = re.compile(rf'(?<!\d)(?<!\d[ .,])({_NUMBER}) ?(?:f ?cfa|xof|cfa|f)\b')
_AMOUNT_PREFIX = re.compile(rf'\b(?:f ?cfa|xof) ?({_NUMBER})(?!\d)')
_NOT_AMOUNT = re.compile(r'(solde|balance|frais|commission|taxe|timbre|bonus)[^.;]{0,25}$')
_DATE_OR_TIME = re.compile(r'(?<!\w)(\d{1,4}[/-]\d{1,2}[/-]\d{1,4}(T\S*)?|\d{1,2}[h:]\d{2}\S*)', re.I)
_PHONE = re.compile(r'(?<!\d)(?:\+?223|00223)?[ .]?(\d{2}[ .]?\d{2}[ .]?\d{2}[ .]?\d{2})(?!\d)')


def _decimal(raw):
    raw = raw.replace(' ', '')
    raw = re.sub(r'[.,](?=\d{3}(?:\D|$))', '', raw).replace(',', '.')
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def is_incoming(text):
    """Vrai seulement si le message annonce de l'argent reçu (et non envoyé, retiré ou annulé)."""
    plain = _plain(text).lower()
    credit, outgoing = _CREDIT.search(plain), _OUTGOING.search(plain)
    return bool(credit) and (outgoing is None or outgoing.start() > credit.end())


def read_amount(text):
    """Premier montant du message qui n'est ni un solde ni des frais. None si rien de sûr."""
    plain = _plain(text).lower()
    found = [(m.start(), m.group(1)) for pattern in (_AMOUNT, _AMOUNT_PREFIX) for m in pattern.finditer(plain)
             if not _NOT_AMOUNT.search(plain[:m.start()])]
    return _decimal(min(found)[1]) if found else None


def read_references(text):
    tokens = re.split(r'[\s:;,()=#]+', _DATE_OR_TIME.sub(' ', _plain(text)))
    return {ref for ref in map(clean_reference, tokens) if is_reference(ref)}


def read_phones(text):
    """Numéros cités dans le message, hors numéros d'encaissement."""
    plain = _DATE_OR_TIME.sub(' ', _plain(text))
    return {clean_phone(m.group(1)) for m in _PHONE.finditer(plain)} - local_numbers() - {''}


# ---------------------------------------------------------------- achats

def open_purchase(user, template):
    """Achat en cours pour ce modèle : réutilisé tant qu'il n'est ni payé ni refusé (évite les doubles paiements)."""
    purchase = TemplatePurchase.objects.filter(
        user=user, template=template, provider=PROVIDER,
        status__in=[TemplatePurchase.PENDING, TemplatePurchase.SUBMITTED]).first()
    if purchase is None:
        return TemplatePurchase.objects.create(user=user, template=template, amount=template.price,
                                               currency=template.currency, provider=PROVIDER), True
    # Le prix a changé et le client n'a encore rien déclaré : le prix affiché s'applique.
    if purchase.status == TemplatePurchase.PENDING and purchase.amount != template.price:
        purchase.amount = template.price
        purchase.save(update_fields=['amount', 'updated_at'])
    return purchase, False


def _reference_taken(operator, reference, exclude):
    return TemplatePurchase.objects.filter(provider=PROVIDER, operator=operator, transaction_reference=reference,
                                           status=TemplatePurchase.PAID).exclude(pk=exclude).exists()


def declare(purchase, operator, phone, reference):
    """Le client annonce son paiement. L'achat est confirmé tout de suite si un message de l'opérateur concorde."""
    phone, reference = clean_phone(phone), clean_reference(reference)
    if purchase.provider != PROVIDER:
        raise PaymentError("Cet achat n'utilise pas ce mode de paiement.")
    if operator not in OPERATORS:
        raise PaymentError('Choisissez votre opérateur : Orange Money, Moov Money ou Wave.')
    if not phone:
        raise PaymentError('Saisissez le numéro qui a payé, sur 8 chiffres (exemple : 76 12 34 56).')
    if phone in local_numbers():
        raise PaymentError("Saisissez VOTRE numéro (celui qui a envoyé l'argent), pas celui du bénéficiaire.")
    if not 6 <= len(reference) <= 40 or sum(c.isdigit() for c in reference) < 4 or clean_phone(reference):
        raise PaymentError("Référence invalide : recopiez l'identifiant de transaction donné par votre opérateur.")
    with transaction.atomic():
        locked = TemplatePurchase.objects.select_for_update().get(pk=purchase.pk)
        if locked.status not in (TemplatePurchase.PENDING, TemplatePurchase.SUBMITTED):
            raise PaymentError('Cet achat est déjà traité.')
        if _reference_taken(operator, reference, exclude=locked.pk):
            raise PaymentError('Cette référence a déjà été utilisée pour un autre achat.')
        first = locked.status == TemplatePurchase.PENDING
        locked.operator, locked.payer_phone, locked.transaction_reference = operator, phone, reference
        locked.status, locked.submitted_at = TemplatePurchase.SUBMITTED, timezone.now()
        locked.save()
    purchase.refresh_from_db()
    match_purchase(purchase)
    if first and purchase.status == TemplatePurchase.SUBMITTED:
        notify_admins(purchase)
    return purchase


def confirm(purchase, *, charged=None, message=None, reviewer=None):
    """Passe l'achat à « payé ». Une référence et un message ne servent qu'une seule fois."""
    try:
        with transaction.atomic():
            locked = TemplatePurchase.objects.select_for_update().get(pk=purchase.pk)
            if locked.provider != PROVIDER or not locked.transaction_reference:
                raise PaymentError("Le client n'a pas encore déclaré ce paiement.")
            if locked.status == TemplatePurchase.PAID:
                raise PaymentError('Ce paiement est déjà confirmé.')
            if message is not None:
                held = PaymentMessage.objects.select_for_update().get(pk=message.pk)
                if held.purchase_id:
                    raise PaymentError('Ce message a déjà confirmé un autre achat.')
                held.purchase = locked
                held.save(update_fields=['purchase'])
            locked.reviewed_by, locked.review_note = reviewer, ''
            locked.save(update_fields=['reviewed_by', 'review_note', 'updated_at'])
            services.mark_paid(locked, locked.transaction_reference, locked.transaction_reference,
                               charged if charged is not None else locked.amount)
    except IntegrityError:
        raise PaymentError('Cette référence a déjà été utilisée pour un autre achat.')
    purchase.refresh_from_db()
    return purchase


def reject(purchase, reason, reviewer):
    with transaction.atomic():
        locked = TemplatePurchase.objects.select_for_update().get(pk=purchase.pk)
        if locked.provider != PROVIDER or locked.status != TemplatePurchase.SUBMITTED:
            raise PaymentError('Seul un paiement en attente de vérification peut être refusé.')
        locked.status, locked.review_note, locked.reviewed_by = TemplatePurchase.FAILED, reason, reviewer
        locked.save()
    purchase.refresh_from_db()
    services.notify_buyer(purchase, f'Paiement non confirmé : modèle « {purchase.template.name} »', reason)
    return purchase


# ---------------------------------------------------------------- rapprochement automatique

def _candidates(purchase):
    return PaymentMessage.objects.filter(purchase=None, operator=purchase.operator, amount__gte=purchase.amount,
                                         received_at__gte=purchase.created_at - CLOCK_TOLERANCE)


def _concordant(purchase, message):
    """Opérateur, montant, date, référence ET numéro (s'il est cité) doivent tous concorder."""
    if message.operator != purchase.operator or message.amount is None or message.amount < purchase.amount:
        return False
    if message.received_at < purchase.created_at - CLOCK_TOLERANCE:
        return False
    if purchase.transaction_reference not in read_references(message.text):
        return False
    phones = read_phones(message.text)
    return not phones or purchase.payer_phone in phones


def _match(purchase, messages):
    for message in messages:
        if _concordant(purchase, message):
            try:
                confirm(purchase, charged=message.amount, message=message)
                return True
            except PaymentError as e:
                logger.warning('Achat %s non confirmé automatiquement : %s', purchase.id, e)
    return False


def match_purchase(purchase):
    if purchase.provider != PROVIDER or purchase.status != TemplatePurchase.SUBMITTED:
        return False
    return _match(purchase, _candidates(purchase))


def suggestions(purchase):
    """Messages probables, proposés à l'administrateur : le numéro ou la référence concorde."""
    if purchase.status not in (TemplatePurchase.SUBMITTED, TemplatePurchase.FAILED):
        return []
    return [m for m in _candidates(purchase)[:50] if purchase.payer_phone in read_phones(m.text)
            or purchase.transaction_reference in read_references(m.text)][:3]


# ---------------------------------------------------------------- téléphone d'encaissement

def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def pair_device(name):
    """Crée un téléphone d'encaissement. Le jeton n'est montré qu'une fois : seule son empreinte est gardée."""
    token = secrets.token_urlsafe(32)
    return PaymentDevice.objects.create(name=name[:80] or 'Téléphone', token_hash=hash_token(token)), token


def authenticate_device(token):
    if not token:
        return None
    return PaymentDevice.objects.filter(token_hash=hash_token(token), is_active=True).first()


def receive_message(device, operator, text, received_at):
    """Enregistre un message d'opérateur (une seule fois) et tente de confirmer l'achat correspondant."""
    text = str(text)[:1000].replace('\x00', '')
    if operator not in OPERATORS or not is_incoming(text):
        return None  # ni opérateur connu ni argent reçu : rien n'est conservé
    received_at = min(received_at, timezone.now())
    fingerprint = hashlib.sha256(f'{operator}|{_plain(text)}|{int(received_at.timestamp())}'.encode()).hexdigest()
    amount = read_amount(text)
    if amount is not None and amount >= Decimal('1e10'):
        amount = None
    message, created = PaymentMessage.objects.get_or_create(fingerprint=fingerprint, defaults={
        'device': device, 'operator': operator, 'text': text, 'amount': amount, 'received_at': received_at})
    if created:
        for purchase in TemplatePurchase.objects.filter(
                provider=PROVIDER, status=TemplatePurchase.SUBMITTED, operator=operator,
                transaction_reference__in=read_references(text)):
            if _match(purchase, [message]):
                break
    return message


def purge_old_messages():
    """Les messages qui n'ont confirmé aucun achat ne sont pas conservés indéfiniment."""
    PaymentMessage.objects.filter(purchase=None, received_at__lt=timezone.now() - KEEP_UNMATCHED_FOR).delete()


# ---------------------------------------------------------------- notifications

def notify_admins(purchase):
    """Prévient les administrateurs qu'un paiement attend leur vérification. Ne bloque jamais la déclaration."""
    label = OPERATORS[purchase.operator]['label']
    admins = list(User.objects.filter(role='ADMIN', is_active=True))
    try:
        from notifications.models import Notification
        for admin in admins:
            Notification.objects.create(
                recipient=admin, verb='Paiement à vérifier', target_type='payment', target_id=purchase.id,
                description=f'{purchase.user.email} : {int(purchase.amount)} FCFA par {label}, '
                            f'référence {purchase.transaction_reference}.')
    except Exception:
        logger.warning('Notification administrateur non créée', exc_info=True)
    recipients = settings.PAYMENT_NOTIFY_EMAILS or [a.email for a in admins]
    if not recipients or not email_configured():
        return
    try:
        send_mail(
            f'Paiement à vérifier : {int(purchase.amount)} FCFA',
            'Un client déclare avoir payé un modèle de mémoire.\n\n'
            f'Modèle : {purchase.template.name}\nClient : {purchase.user.email}\n'
            f'Montant attendu : {int(purchase.amount)} FCFA\nOpérateur : {label}\n'
            f'Numéro du payeur : {purchase.payer_phone}\nRéférence : {purchase.transaction_reference}\n\n'
            "Vérifiez que l'argent est bien arrivé sur votre compte AVANT de valider :\n"
            f'{settings.FRONTEND_URL}/admin\n',
            settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)
    except Exception:
        logger.exception('Email « paiement à vérifier » non envoyé')
