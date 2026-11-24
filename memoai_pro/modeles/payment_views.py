"""Points d'entrée de l'API de paiement mobile money (règles : mobile_money.py).

GET    /modeles/paiement/                             moyens de paiement et numéro d'encaissement
POST   /modeles/paiement/messages/                    messages transmis par le téléphone d'encaissement
GET    /modeles/admin/paiements/?etat=tous            paiements (administrateur ; par défaut : à vérifier)
POST   /modeles/admin/paiements/<id>/approve/         {message_id?} confirme un paiement vérifié
POST   /modeles/admin/paiements/<id>/reject/          {reason} refuse un paiement
GET    /modeles/admin/paiements/messages/             derniers messages reçus
GET, POST /modeles/admin/telephones/ ; DELETE <id>/   téléphones d'encaissement
"""
from datetime import datetime, timezone as dt_timezone

from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import IsAdminRole
from . import mobile_money
from .models import PaymentDevice, PaymentMessage, TemplatePurchase
from .serializers import AdminPaymentSerializer, PaymentDeviceSerializer, PaymentMessageSerializer

MAX_MESSAGES = 20


class PaymentOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not mobile_money.is_enabled():
            return Response({'mode': 'jemeni'})
        return Response({'mode': 'mobile_money', **mobile_money.options()})


class DeviceMessagesView(APIView):
    """Reçoit les messages « argent reçu ». Authentification : en-tête X-Device-Token (téléphone jumelé).
    Une liste vide sert de signal de présence."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        device = mobile_money.authenticate_device(request.headers.get('X-Device-Token', ''))
        if device is None:
            return Response({'error': 'Téléphone non autorisé.'}, status=status.HTTP_401_UNAUTHORIZED)
        messages = request.data.get('messages') if isinstance(request.data, dict) else None
        if not isinstance(messages, list) or len(messages) > MAX_MESSAGES:
            raise ValidationError({'error': f'« messages » : liste de {MAX_MESSAGES} éléments au plus.'})
        PaymentDevice.objects.filter(pk=device.pk).update(last_seen_at=timezone.now())
        kept = 0
        for item in messages:
            if not isinstance(item, dict) or not isinstance(item.get('text'), str):
                continue
            try:
                received_at = datetime.fromtimestamp(int(item.get('received_at')) / 1000, tz=dt_timezone.utc)
            except (TypeError, ValueError, OverflowError, OSError):
                received_at = timezone.now()
            if mobile_money.receive_message(device, str(item.get('operator')), item['text'], received_at):
                kept += 1
        if messages:
            mobile_money.purge_old_messages()
        return Response({'status': 'ok', 'kept': kept})


class AdminPaymentViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = AdminPaymentSerializer
    permission_classes = [IsAdminRole]
    pagination_class = None

    def get_queryset(self):
        return (TemplatePurchase.objects.filter(provider=mobile_money.PROVIDER)
                .exclude(status=TemplatePurchase.PENDING).select_related('user', 'template').order_by('-submitted_at'))

    def list(self, request, *args, **kwargs):
        payments = self.get_queryset()
        if request.query_params.get('etat') != 'tous':
            payments = payments.filter(status=TemplatePurchase.SUBMITTED)
        return Response(self.get_serializer(payments[:100], many=True).data)

    def _run(self, func, *args, **kwargs):
        try:
            purchase = func(*args, **kwargs)
        except mobile_money.PaymentError as e:
            raise ValidationError({'error': str(e)})
        return Response(self.get_serializer(purchase).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        purchase = self.get_object()
        message, message_id = None, request.data.get('message_id')
        if message_id is not None:
            message = next((m for m in mobile_money.suggestions(purchase) if str(m.pk) == str(message_id)), None)
            if message is None:
                raise ValidationError({'error': 'Ce message ne correspond plus à ce paiement.'})
        return self._run(mobile_money.confirm, purchase, message=message, reviewer=request.user,
                         charged=message.amount if message else None)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        reason = str(request.data.get('reason') or '').strip()[:255]
        if not reason:
            raise ValidationError({'error': 'Indiquez au client la raison du refus.'})
        return self._run(mobile_money.reject, self.get_object(), reason, request.user)

    @action(detail=False, methods=['get'])
    def messages(self, request):
        return Response(PaymentMessageSerializer(PaymentMessage.objects.all()[:30], many=True).data)


class AdminDeviceViewSet(mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    queryset = PaymentDevice.objects.all()
    serializer_class = PaymentDeviceSerializer
    permission_classes = [IsAdminRole]
    pagination_class = None

    def create(self, request):
        device, token = mobile_money.pair_device(str(request.data.get('name') or '').strip())
        return Response({**self.get_serializer(device).data, 'token': token}, status=status.HTTP_201_CREATED)
