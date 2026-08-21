import logging
import requests
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import RegisterSerializer, ProfileSerializer

logger = logging.getLogger(__name__)

class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': ProfileSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(email=email, password=password)
        if user and user.is_active:
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': ProfileSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response(ProfileSerializer(request.user).data)
    def put(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'status': 'logged out'})
        except Exception:
            return Response({'status': 'already logged out'}, status=status.HTTP_400_BAD_REQUEST)

class Request2FAView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        code = get_random_string(length=6, allowed_chars='0123456789')
        request.user.totp_code = code  # ajouter ce champ au modèle User
        request.user.save()
        send_mail(
            'Code 2FA MemoAI Pro',
            f'Votre code est : {code}',
            settings.DEFAULT_FROM_EMAIL,
            [request.user.email],
            fail_silently=False,
        )
        return Response({'message': 'Code envoyé par email'})

class Verify2FAView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        code = request.data.get('code')
        if request.user.totp_code == code:
            request.user.is_verified = True  # ajouter ce champ
            request.user.save()
            return Response({'verified': True})
        return Response({'error': 'Code invalide'}, status=400)

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        old = request.data.get('old_password')
        new = request.data.get('new_password')
        if not request.user.check_password(old):
            return Response({'error': 'Ancien mot de passe incorrect'}, status=400)
        request.user.set_password(new)
        request.user.save()
        return Response({'status': 'password updated'})

class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user
        # Exporter les données (RGPD) avant suppression
        # ...
        user.delete()
        return Response({'status': 'account deleted'})
class GoogleOAuthView(APIView):
    def post(self, request):
        token = request.data.get('id_token')
        # Vérifier le token avec Google
        resp = requests.get(
            'https://oauth2.googleapis.com/tokeninfo',
            params={'id_token': token}
        )
        if resp.status_code != 200:
            return Response({'error': 'Invalid token'}, status=400)
        data = resp.json()
        email = data.get('email')
        if not email:
            return Response({'error': 'Email not found'}, status=400)
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': data.get('given_name', ''),
                'last_name': data.get('family_name', ''),
                'role': 'STUDENT'
            }
        )
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': ProfileSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })