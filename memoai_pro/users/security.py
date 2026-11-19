"""Protection des comptes contre la force brute.

- Chaque échec de connexion est compté par adresse email (quelle que soit l'adresse IP de l'attaquant).
- Au-delà de LOGIN_MAX_FAILURES échecs, le compte est verrouillé LOGIN_LOCKOUT_MINUTES minutes.
- Un compte qui n'existe pas est traité exactement comme un compte existant (pas d'indice pour l'attaquant).
"""
import hashlib
import logging
import math
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.cache import cache

logger = logging.getLogger('security')


def _key(email):
    digest = hashlib.sha256(email.strip().lower().encode()).hexdigest()[:32]
    return f'login-fail:{digest}'


def lockout_remaining(email):
    """Minutes de verrouillage restantes (0 si le compte n'est pas verrouillé)."""
    if not email:
        return 0
    state = cache.get(_key(email)) or {}
    until = state.get('locked_until', 0)
    left = until - time.time()
    return math.ceil(left / 60) if left > 0 else 0


def record_failure(email, request=None):
    if not email:
        return
    window = settings.LOGIN_LOCKOUT_MINUTES * 60
    state = cache.get(_key(email)) or {'count': 0}
    state['count'] = state.get('count', 0) + 1
    if state['count'] >= settings.LOGIN_MAX_FAILURES:
        state = {'count': 0, 'locked_until': time.time() + window}
        ip = request.META.get('REMOTE_ADDR', '?') if request else '?'
        logger.warning('Compte verrouillé après trop d’échecs de connexion (ip=%s)', ip)
    cache.set(_key(email), state, window)


def clear_failures(email):
    if email:
        cache.delete(_key(email))


def revoke_all_tokens(user):
    """Invalide tous les jetons de rafraîchissement de l'utilisateur (déconnexion de tous les appareils)."""
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


class LockoutModelBackend(ModelBackend):
    """Authentification Django (API et administration) avec verrouillage après trop d'échecs."""

    def authenticate(self, request, username=None, password=None, **extra):
        email = str(username or extra.get(get_user_model().USERNAME_FIELD) or '')
        if lockout_remaining(email):
            return None
        user = super().authenticate(request, username=username, password=password, **extra)
        if user is None:
            record_failure(email, request)
        else:
            clear_failures(email)
        return user
