import logging
import requests
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from django.db.models import Count, Q, Sum
from rest_framework import filters, generics, mixins, viewsets
from rest_framework.exceptions import ValidationError

from .models import User
from .permissions import IsAdminRole
from .serializers import (
    AdminUserSerializer, ProfileSerializer, RegisterSerializer, UserPublicSerializer,
)

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
        # Chaque espace de connexion (étudiant, encadreur, jury...) envoie
        # le rôle attendu : on refuse un compte d'un autre rôle.
        expected_role = request.data.get('role')
        user = authenticate(email=email, password=password)
        if user and user.is_active:
            if expected_role and user.role != expected_role:
                return Response({
                    'error': f"Ce compte est enregistré en tant que « {user.get_role_display()} ». "
                             "Utilisez l'espace de connexion correspondant.",
                    'role': user.role,
                }, status=status.HTTP_403_FORBIDDEN)
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
        request.user.totp_code = code
        request.user.save(update_fields=['totp_code'])
        try:
            send_mail(
                'Code 2FA MemoAI Pro',
                f'Votre code est : {code}',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
                fail_silently=False,
            )
        except Exception:
            logger.exception("Envoi du code 2FA impossible")
            return Response({'error': "L'email n'a pas pu être envoyé. Réessayez plus tard."}, status=503)
        return Response({'message': 'Code envoyé par email'})

class Verify2FAView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        code = request.data.get('code')
        if code and request.user.totp_code == code:
            request.user.two_factor_enabled = True
            request.user.totp_code = ''
            request.user.save(update_fields=['two_factor_enabled', 'totp_code'])
            return Response({'verified': True})
        return Response({'error': 'Code invalide'}, status=400)

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        old = request.data.get('old_password')
        new = request.data.get('new_password')
        if not old or not request.user.check_password(old):
            return Response({'error': 'Ancien mot de passe incorrect'}, status=400)
        try:
            validate_password(new or '', request.user)
        except DjangoValidationError as e:
            return Response({'error': ' '.join(e.messages)}, status=400)
        request.user.set_password(new)
        request.user.save(update_fields=['password'])
        return Response({'status': 'password updated'})

class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user
        if not user.check_password(request.data.get('password') or ''):
            return Response({'error': 'Mot de passe incorrect.'}, status=400)
        user.delete()
        return Response({'status': 'account deleted'})
class GoogleOAuthView(APIView):
    def post(self, request):
        token = request.data.get('id_token')
        if not token:
            return Response({'error': 'id_token requis'}, status=400)
        try:
            resp = requests.get('https://oauth2.googleapis.com/tokeninfo', params={'id_token': token}, timeout=10)
        except requests.RequestException:
            return Response({'error': 'Google est injoignable. Réessayez plus tard.'}, status=502)
        if resp.status_code != 200:
            return Response({'error': 'Invalid token'}, status=400)
        data = resp.json()
        email = data.get('email')
        if not email or str(data.get('email_verified')).lower() != 'true':
            return Response({'error': 'Email Google non vérifié'}, status=400)
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User.objects.create_user(
                email, None, first_name=data.get('given_name', ''), last_name=data.get('family_name', ''),
                role='STUDENT', email_verified=True,
            )
        if not user.is_active:
            return Response({'error': 'Ce compte est suspendu.'}, status=403)
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': ProfileSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })


class UserDirectoryView(generics.ListAPIView):
    """Annuaire des encadreurs, co-encadreurs et jurys, pour que l'étudiant
    puisse les rattacher à son mémoire. Filtres : ?role=SUPERVISOR&search=..."""
    serializer_class = UserPublicSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['first_name', 'last_name', 'email', 'university', 'speciality']

    def get_queryset(self):
        roles = self.request.query_params.get('role', ','.join(User.REVIEWER_ROLES)).split(',')
        roles = [r for r in roles if r in User.REVIEWER_ROLES]
        return User.objects.filter(role__in=roles, is_active=True).order_by('last_name', 'first_name')


class AdminUserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                       mixins.UpdateModelMixin, mixins.DestroyModelMixin,
                       viewsets.GenericViewSet):
    """Gestion des utilisateurs : liste, changement de rôle, suspension, suppression."""
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminRole]
    filter_backends = [filters.SearchFilter]
    search_fields = ['first_name', 'last_name', 'email', 'university']

    def get_queryset(self):
        qs = User.objects.annotate(projects_count=Count('projects')).order_by('-created_at')
        role = self.request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)
        return qs

    def perform_update(self, serializer):
        data = serializer.validated_data
        if serializer.instance == self.request.user and (
            data.get('role', 'ADMIN') != 'ADMIN' or data.get('is_active') is False
        ):
            raise ValidationError({'error': 'Vous ne pouvez pas retirer vos propres droits administrateur.'})
        serializer.save()

    def perform_destroy(self, instance):
        if instance == self.request.user:
            raise ValidationError({'error': 'Vous ne pouvez pas supprimer votre propre compte ici.'})
        instance.delete()


class AdminStatsView(APIView):
    """Tableau de bord administrateur (§3.17)."""
    permission_classes = [IsAdminRole]

    def get(self, request):
        from projects.models import Project
        from payments.models import Transaction
        from ai.models import AIGenerationTask

        users_by_role = dict(User.objects.values_list('role').annotate(n=Count('id')))
        projects_by_status = dict(Project.objects.values_list('status').annotate(n=Count('id')))
        payments = Transaction.objects.aggregate(
            revenue=Sum('amount', filter=Q(status='SUCCESS')),
            succeeded=Count('id', filter=Q(status='SUCCESS')),
            total=Count('id'),
        )
        from modeles.models import TemplatePurchase
        templates = TemplatePurchase.objects.filter(status=TemplatePurchase.PAID).aggregate(
            revenue=Sum('amount'), sold=Count('id'),
        )
        students = users_by_role.get('STUDENT', 0)
        return Response({
            'users_total': User.objects.count(),
            'users_active': User.objects.filter(is_active=True).count(),
            'users_by_role': users_by_role,
            'projects_total': Project.objects.count(),
            'projects_by_status': projects_by_status,
            'payments_total': payments['total'],
            'payments_succeeded': payments['succeeded'],
            'revenue': float(payments['revenue'] or 0),
            'conversion_rate': round(100 * payments['succeeded'] / students, 1) if students else 0,
            'ai_tasks_total': AIGenerationTask.objects.count(),
            'templates_sold': templates['sold'],
            'templates_revenue': float(templates['revenue'] or 0),
        })
