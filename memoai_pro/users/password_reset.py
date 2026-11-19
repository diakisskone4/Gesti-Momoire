"""Mot de passe oublié : réinitialisation par un lien envoyé à l'adresse email du compte.

POST /users/password-reset/          {email, role?}        → toujours la même réponse (aucun indice
                                                              sur l'existence d'un compte)
POST /users/password-reset/confirm/  {uid, token, new_password}

Le lien expire au bout de PASSWORD_RESET_TIMEOUT (1 heure) et ne sert qu'une fois : le jeton
dépend du mot de passe actuel, il devient invalide dès que celui-ci change.
"""
import logging
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import EmailMultiAlternatives
from django.utils.encoding import force_bytes, force_str
from django.utils.html import escape
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import security
from .models import User

logger = logging.getLogger(__name__)

GENERIC_ANSWER = ("Si un compte correspond à cette adresse, un email contenant un lien de réinitialisation "
                  "vient d'être envoyé. Pensez à vérifier vos courriers indésirables (spam).")
ROLE_SLUGS = {'STUDENT': 'etudiant', 'SUPERVISOR': 'encadreur', 'CO_SUPERVISOR': 'co-encadreur',
              'JURY': 'jury', 'ADMIN': 'admin'}
_NO_DELIVERY = ('console', 'locmem', 'dummy', 'filebased')


def email_configured():
    """Faux si les emails ne partent nulle part (affichage console, mémoire...) hors développement."""
    if settings.DEBUG or getattr(settings, 'TESTING', False):
        return True
    return not any(word in settings.EMAIL_BACKEND for word in _NO_DELIVERY)


def reset_link(user):
    query = urlencode({
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': default_token_generator.make_token(user),
        'espace': ROLE_SLUGS.get(user.role, 'etudiant'),
    })
    return f'{settings.FRONTEND_URL}/reinitialiser-mot-de-passe?{query}'


def send_reset_email(user):
    link = reset_link(user)
    minutes = settings.PASSWORD_RESET_TIMEOUT // 60
    name = user.first_name or user.email
    text = (
        f"Bonjour {name},\n\n"
        "Vous avez demandé à réinitialiser le mot de passe de votre compte MemoAI Pro.\n"
        f"Cliquez sur ce lien pour choisir un nouveau mot de passe (valable {minutes} minutes) :\n\n"
        f"{link}\n\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez cet email : votre mot de passe reste inchangé.\n\n"
        "L'équipe MemoAI Pro"
    )
    html = f"""<!doctype html><html lang="fr"><body style="margin:0;background:#f4f7f6;font-family:Arial,sans-serif;color:#1f2937">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:32px 12px">
<table role="presentation" width="100%" style="max-width:520px;background:#ffffff;border-radius:14px;padding:32px" cellpadding="0" cellspacing="0">
<tr><td style="font-size:20px;font-weight:bold;color:#0f766e;padding-bottom:16px">MemoAI Pro</td></tr>
<tr><td style="font-size:15px;line-height:1.6">
<p>Bonjour {escape(name)},</p>
<p>Vous avez demandé à réinitialiser le mot de passe de votre compte.</p>
<p style="text-align:center;padding:12px 0">
<a href="{escape(link)}" style="background:#0f766e;color:#ffffff;text-decoration:none;padding:13px 26px;border-radius:10px;font-weight:bold;display:inline-block">Choisir un nouveau mot de passe</a></p>
<p style="font-size:13px;color:#6b7280">Ce lien est valable {minutes} minutes et ne peut servir qu'une seule fois.</p>
<p style="font-size:13px;color:#6b7280">Si vous n'êtes pas à l'origine de cette demande, ignorez cet email : votre mot de passe reste inchangé.</p>
</td></tr></table></td></tr></table></body></html>"""
    message = EmailMultiAlternatives('Réinitialisation de votre mot de passe MemoAI Pro', text,
                                     settings.DEFAULT_FROM_EMAIL, [user.email])
    message.attach_alternative(html, 'text/html')
    message.send(fail_silently=False)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = 'password_reset'

    def post(self, request):
        email = str(request.data.get('email') or '').strip()[:254]
        if '@' not in email:
            return Response({'error': 'Saisissez une adresse email valide.'}, status=status.HTTP_400_BAD_REQUEST)
        if not email_configured():
            logger.error("Mot de passe oublié : aucun serveur d'envoi d'emails configuré (EMAIL_BACKEND).")
            return Response({'error': "L'envoi d'emails n'est pas encore configuré sur la plateforme. "
                                      "Contactez l'administrateur."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is not None and user.has_usable_password():
            try:
                send_reset_email(user)
            except Exception:  # serveur SMTP indisponible, identifiants invalides...
                logger.exception("Envoi de l'email de réinitialisation impossible")
                return Response({'error': "L'email n'a pas pu être envoyé. Réessayez dans quelques minutes."},
                                status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({'message': GENERIC_ANSWER})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = 'password_reset_confirm'

    def post(self, request):
        invalid = Response({'error': 'Ce lien de réinitialisation est invalide ou a expiré. '
                                     'Faites une nouvelle demande.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            pk = force_str(urlsafe_base64_decode(str(request.data.get('uid') or '')))
            user = User.objects.get(pk=int(pk), is_active=True)
        except (ValueError, TypeError, OverflowError, User.DoesNotExist):
            return invalid
        if not default_token_generator.check_token(user, str(request.data.get('token') or '')):
            return invalid
        password = str(request.data.get('new_password') or '')
        try:
            validate_password(password, user)
        except DjangoValidationError as e:
            return Response({'error': ' '.join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(password)
        user.save(update_fields=['password'])
        security.revoke_all_tokens(user)      # déconnecte tous les appareils
        security.clear_failures(user.email)   # lève un éventuel verrouillage du compte
        return Response({'message': 'Votre mot de passe a été modifié. Vous pouvez vous connecter.',
                         'role': user.role})
