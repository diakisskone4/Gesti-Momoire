"""Client minimal de l'API Jɛmɛnipay (https://jemeni.net/docs).

- Paiement par page hébergée : POST /payments/checkout renvoie une `checkout_url` (valable 30 minutes).
- Confirmation : GET /payments/{id} (état 2 = payé).
- Chaque requête est signée : HMAC-SHA512(SK + AK + MÉTHODE + URL + CORPS + TIMESTAMP, clé = SK).
- Webhooks signés : X-Jemeni-Signature = HMAC-SHA512(corps brut, secret du webhook).

Le mode (test ou réel) découle de la clé publique : pk_live_… = argent réel, sinon bac à sable.
"""
import hashlib
import hmac
import json
import logging
import time
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TIMEOUT = 20

# Identifiants enregistrés dans TemplatePurchase.provider
PROVIDER_LIVE, PROVIDER_TEST = 'jemeni', 'jemeni_test'

# États d'une transaction Jɛmɛnipay
STATE_COMPLETED = 2
STATES_FAILED = {3, 4}  # refusée / expirée, annulée


class JemeniError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


def is_sandbox():
    return not settings.JEMENI_PUBLIC_KEY.startswith('pk_live_')


def provider():
    return PROVIDER_TEST if is_sandbox() else PROVIDER_LIVE


def base_url(sandbox):
    return f"{settings.JEMENI_API_URL.rstrip('/')}/{'sandbox' if sandbox else 'live'}"


def sign(method, url, body, timestamp):
    sk, ak = settings.JEMENI_SECRET_KEY, settings.JEMENI_PUBLIC_KEY
    message = f'{sk}{ak}{method}{url}{body}{timestamp}'
    return hmac.new(sk.encode(), message.encode(), hashlib.sha512).hexdigest()


def _call(method, path, payload=None):
    if not (settings.JEMENI_PUBLIC_KEY and settings.JEMENI_SECRET_KEY and settings.JEMENI_TOKEN):
        raise JemeniError("Le paiement n'est pas configuré (clés Jɛmɛnipay manquantes).", 503)
    sandbox = is_sandbox()
    url = base_url(sandbox) + path
    # La signature porte sur le corps exact : il est sérialisé une seule fois et envoyé tel quel.
    body = json.dumps(payload, ensure_ascii=False, separators=(',', ':')) if payload is not None else ''
    timestamp = str(int(time.time()))
    headers = {
        'Accept': 'application/json',
        'auth-apiKey': settings.JEMENI_PUBLIC_KEY,
        'auth-token': settings.JEMENI_TOKEN,
        'auth-timestamp': timestamp,
        'auth-signature': sign(method, url, body, timestamp),
    }
    if sandbox:
        headers['sandbox'] = 'true'
    if payload is not None:
        headers['Content-Type'] = 'application/json'
    try:
        response = requests.request(method, url, data=body.encode() if payload is not None else None,
                                    headers=headers, timeout=TIMEOUT, allow_redirects=False)
    except requests.RequestException as e:
        logger.error('Jemeni injoignable (%s %s): %s', method, path, e)
        raise JemeniError('Le service de paiement est injoignable. Réessayez dans un instant.')
    try:
        result = response.json()
    except ValueError:
        result = {}
    if not isinstance(result, dict):
        result = {}
    data = result.get('data')
    if response.status_code >= 300 or str(result.get('status', '')).lower() != 'success' or not isinstance(data, dict):
        logger.error('Jemeni %s %s -> %s %s', method, path, response.status_code, str(result)[:500])
        if response.status_code in (401, 403):
            raise JemeniError("Le paiement est mal configuré (clés Jɛmɛnipay refusées). Contactez l'administrateur.", 503)
        if response.status_code == 429:
            raise JemeniError('Trop de demandes de paiement. Réessayez dans une minute.', 429)
        raise JemeniError('Le service de paiement a refusé la demande. Réessayez plus tard.')
    return data


def create_checkout(*, amount, currency, description, reference, return_url, metadata):
    """Crée la page de paiement. Renvoie {'id': transaction, 'checkout_url', 'reference'}."""
    amount = Decimal(amount)
    if currency != 'XOF' or amount != amount.to_integral_value() or amount < 100:
        raise JemeniError('Jɛmɛnipay accepte uniquement des montants entiers en FCFA (100 minimum).', 400)
    data = _call('POST', '/payments/checkout', {
        'amount': int(amount),
        'country_code': settings.JEMENI_COUNTRY,
        'source': 'MemoAI Pro',
        'description': description[:255],
        'reference': reference[:100],
        'return_url': return_url,
        'metadata': metadata,
    })
    transaction = data.get('transaction') or {}
    if not transaction.get('id') or not str(data.get('checkout_url') or '').startswith('https://'):
        logger.error('Jemeni: réponse de checkout inattendue: %s', str(data)[:500])
        raise JemeniError('Réponse inattendue du service de paiement.')
    return {'id': str(transaction['id']), 'checkout_url': data['checkout_url'],
            'reference': str(transaction.get('reference') or '')}


def get_payment(transaction_id):
    return _call('GET', f'/payments/{transaction_id}')


def to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None


def to_state(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def is_valid_webhook(raw_body: bytes, signature: str) -> bool:
    secret = settings.JEMENI_WEBHOOK_SECRET
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected.encode(), signature.strip().lower().encode('utf-8', 'replace'))
