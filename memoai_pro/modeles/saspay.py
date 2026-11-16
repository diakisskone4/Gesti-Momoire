"""Client minimal de l'API SasPay (https://docs.saspay.me).

- Paiement par checkout hébergé : POST /checkout-sessions/ renvoie un `checkout_url`.
- Confirmation : GET /checkout-sessions/{id}/status/ puis GET /payments/{transaction_id}/verify/.
- Webhooks signés : HMAC-SHA256 de "{timestamp}.{corps brut}" (en-têtes X-Webhook-*).
"""
import hashlib
import hmac
import logging
import time
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TIMEOUT = 20
WEBHOOK_TOLERANCE_SECONDS = 300


class SasPayError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


def _headers():
    if not settings.SASPAY_SECRET_KEY:
        raise SasPayError("Le paiement n'est pas configuré (SASPAY_SECRET_KEY manquante).", 503)
    return {'Authorization': f'Bearer {settings.SASPAY_SECRET_KEY}', 'Content-Type': 'application/json',
            'Accept': 'application/json'}


def _call(method, path, payload=None):
    url = settings.SASPAY_API_URL.rstrip('/') + path
    try:
        response = requests.request(method, url, json=payload, headers=_headers(), timeout=TIMEOUT)
    except requests.RequestException as e:
        logger.error('SasPay injoignable (%s %s): %s', method, path, e)
        raise SasPayError('Le service de paiement est injoignable. Réessayez dans un instant.')
    try:
        body = response.json()
    except ValueError:
        body = {}
    if response.status_code >= 400:
        logger.error('SasPay %s %s -> %s %s', method, path, response.status_code, str(body)[:500])
        if response.status_code in (401, 403):
            raise SasPayError("Le paiement est mal configuré (clé SasPay refusée). Contactez l'administrateur.", 503)
        if response.status_code == 429:
            raise SasPayError('Trop de demandes de paiement. Réessayez dans une minute.', 429)
        raise SasPayError('Le service de paiement a refusé la demande. Réessayez plus tard.')
    # Les réponses peuvent être enveloppées dans {"success", "data"}.
    if isinstance(body, dict) and isinstance(body.get('data'), dict):
        return body['data']
    return body


def create_checkout_session(*, amount, currency, customer_email, customer_name, description, return_url,
                            metadata, country=None, customer_phone=''):
    payload = {
        'amount': f'{Decimal(amount):.2f}',
        'currency': currency,
        'customer_email': customer_email,
        'customer_name': customer_name or customer_email,
        'description': description[:255],
        'return_url': return_url,
        'metadata': metadata,
    }
    if country:
        payload['country'] = country
    if customer_phone:
        payload['customer_phone'] = customer_phone
    data = _call('POST', '/checkout-sessions/', payload)
    if not data.get('id') or not data.get('checkout_url'):
        logger.error('SasPay: réponse de checkout inattendue: %s', str(data)[:500])
        raise SasPayError('Réponse inattendue du service de paiement.')
    return data


def checkout_status(session_id):
    return _call('GET', f'/checkout-sessions/{session_id}/status/')


def verify_payment(transaction_id):
    return _call('GET', f'/payments/{transaction_id}/verify/')


def to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None


def is_valid_webhook(raw_body: bytes, signature: str, timestamp: str) -> bool:
    secret = settings.SASPAY_WEBHOOK_SECRET
    if not secret or not signature or not timestamp:
        return False
    try:
        if abs(int(time.time()) - int(timestamp)) > WEBHOOK_TOLERANCE_SECONDS:
            return False
    except ValueError:
        return False
    signed = f'{timestamp}.'.encode() + raw_body
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip().lower())
