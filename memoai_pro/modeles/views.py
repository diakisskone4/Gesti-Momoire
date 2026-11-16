import json
import logging
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.access import get_owned_project, get_readable_project
from . import saspay, services
from .covers import cover_data, render_cover_html
from .models import MemoirTemplate, TemplatePurchase
from .serializers import MemoirTemplateSerializer, TemplatePurchaseSerializer

logger = logging.getLogger(__name__)


def owned_template_ids(user):
    return set(TemplatePurchase.objects.filter(user=user, status=TemplatePurchase.PAID)
               .values_list('template_id', flat=True))


def saspay_error(e):
    return Response({'error': str(e)}, status=e.status)


class MemoirTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """Catalogue des modèles de mémoire.

    GET  /modeles/                      catalogue (+ owned, aperçu du plan)
    GET  /modeles/<slug>/               détail (plan complet si acheté)
    GET  /modeles/<slug>/cover/         page de garde d'exemple (HTML, filigrane si non acheté)
    POST /modeles/<slug>/purchase/      crée la session de paiement SasPay → {checkout_url}
    POST /modeles/<slug>/apply/         applique le modèle acheté à un mémoire {project_id}
    """
    serializer_class = MemoirTemplateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'

    def get_queryset(self):
        return MemoirTemplate.objects.filter(is_active=True)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if self.request.user.is_authenticated:
            ctx['owned_ids'] = owned_template_ids(self.request.user)
        return ctx

    @action(detail=True, methods=['get'])
    def cover(self, request, slug=None):
        template = self.get_object()
        owned = template.id in owned_template_ids(request.user)
        return Response({'html': render_cover_html(template, cover_data(template), watermark=not owned)})

    @action(detail=True, methods=['post'])
    def purchase(self, request, slug=None):
        template = self.get_object()
        user = request.user
        if template.is_owned_by(user):
            raise ValidationError({'error': 'Vous possédez déjà ce modèle.'})

        pending = services.reusable_pending_purchase(user, template)
        if pending:
            return Response(TemplatePurchaseSerializer(pending).data)

        purchase = TemplatePurchase.objects.create(
            user=user, template=template, amount=template.price, currency=template.currency,
        )
        try:
            session = saspay.create_checkout_session(
                amount=template.price,
                currency=template.currency,
                customer_email=user.email,
                customer_name=user.full_name,
                customer_phone=user.phone,
                description=f'MemoAI Pro — Modèle « {template.name} »',
                return_url=f'{settings.FRONTEND_URL}/modeles?achat={purchase.id}',
                metadata={'purchase_id': purchase.id, 'user_id': user.id, 'template': template.slug},
                country=settings.SASPAY_DEFAULT_COUNTRY or None,
            )
        except saspay.SasPayError as e:
            purchase.status = TemplatePurchase.FAILED
            purchase.save(update_fields=['status', 'updated_at'])
            return saspay_error(e)

        purchase.checkout_session_id = session['id']
        purchase.checkout_url = session['checkout_url']
        purchase.save(update_fields=['checkout_session_id', 'checkout_url', 'updated_at'])
        return Response(TemplatePurchaseSerializer(purchase).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def apply(self, request, slug=None):
        template = self.get_object()
        if not template.is_owned_by(request.user):
            return Response({'error': "Achetez ce modèle pour l'utiliser."}, status=status.HTTP_402_PAYMENT_REQUIRED)
        project = get_owned_project(request.user, request.data.get('project_id'))
        if project.status in ('REVIEW', 'VALIDATED'):
            raise ValidationError({'error': 'Ce mémoire est en relecture ou validé : il ne peut plus être restructuré.'})
        created = services.apply_template(template, project)
        return Response({'project_id': project.id, 'chapters_created': created})


class TemplatePurchaseViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Achats de l'utilisateur. POST /modeles/achats/<id>/verify/ confirme le paiement auprès de SasPay."""
    serializer_class = TemplatePurchaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return TemplatePurchase.objects.none()
        return TemplatePurchase.objects.filter(user=self.request.user).select_related('template')

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        purchase = self.get_object()
        try:
            services.refresh_purchase(purchase)
        except saspay.SasPayError as e:
            return saspay_error(e)
        return Response(self.get_serializer(purchase).data)


class ProjectCoverView(APIView):
    """Page de garde d'un mémoire, remplie avec ses informations : GET /modeles/projects/<id>/cover/."""
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = get_readable_project(request.user, project_id)
        if not project.template_id:
            return Response({'error': "Ce mémoire n'utilise pas de modèle."}, status=404)
        if not project.template.is_owned_by(project.user):
            raise PermissionDenied("Le modèle de ce mémoire n'a pas été acheté.")
        html = render_cover_html(project.template, cover_data(project.template, project))
        if request.query_params.get('format') == 'html':
            return HttpResponse(html, content_type='text/html; charset=utf-8')
        return Response({'html': html})


@csrf_exempt
@require_POST
def saspay_webhook(request):
    """Webhook SasPay (événements transaction.*), signé en HMAC-SHA256.
    Le contenu n'est jamais cru tel quel : on revérifie l'achat auprès de l'API."""
    if not saspay.is_valid_webhook(request.body, request.headers.get('X-Webhook-Signature', ''),
                                   request.headers.get('X-Webhook-Timestamp', '')):
        return JsonResponse({'error': 'Signature invalide'}, status=401)
    try:
        payload = json.loads(request.body)
    except ValueError:
        return JsonResponse({'error': 'JSON invalide'}, status=400)

    event = payload.get('event', '')
    data = payload.get('data') or {}
    if not event.startswith('transaction.'):
        return JsonResponse({'status': 'ignored'})

    tx_id, reference = str(data.get('id') or ''), str(data.get('reference') or '')
    lookup = Q(transaction_id=tx_id) if tx_id else Q(pk__in=[])
    if reference:
        lookup |= Q(transaction_reference=reference)
    purchases = list(TemplatePurchase.objects.filter(lookup, status=TemplatePurchase.PENDING))
    if not purchases:
        # Le webhook ne contient pas l'identifiant de session : on revérifie les achats en attente récents.
        purchases = list(TemplatePurchase.objects.filter(
            status=TemplatePurchase.PENDING, created_at__gte=timezone.now() - timedelta(days=1),
        ).exclude(checkout_session_id='')[:25])
    for purchase in purchases:
        try:
            services.refresh_purchase(purchase)
        except saspay.SasPayError:
            logger.warning('Webhook SasPay : vérification impossible pour l\'achat %s', purchase.id)
            return JsonResponse({'error': 'Vérification temporairement impossible'}, status=503)  # SasPay réessaiera
    return JsonResponse({'status': 'ok'})
