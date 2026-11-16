"""Authentification des WebSockets par jeton JWT : ws://.../?token=<access>."""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def user_from_token(raw_token):
    from rest_framework_simplejwt.authentication import JWTAuthentication
    from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

    auth = JWTAuthentication()
    try:
        user = auth.get_user(auth.get_validated_token(raw_token))
    except (InvalidToken, TokenError, Exception):
        return AnonymousUser()
    return user if user.is_active else AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        token = parse_qs(scope.get('query_string', b'').decode()).get('token', [None])[0]
        if token:
            scope['user'] = await user_from_token(token)
        else:
            scope.setdefault('user', AnonymousUser())
        return await super().__call__(scope, receive, send)
