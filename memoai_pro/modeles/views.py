import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.access import get_owned_project, get_readable_project
from . import jemeni, mobile_money, services
from .covers import cover_data, render_cover_html
from .models import MemoirTemplate, TemplatePurchase
from .serializers import MemoirTemplateSerializer, TemplatePurchaseSerializer

logger = logging.getLogger(__name__)


def owned_template_ids(user):
    """Modèles achetés par l'utilisateur + modèles gratuits (disponibles pour tous)."""
    paid = TemplatePurchase.valid().filter(user=user).values_list('template_id', flat=True)
    free = MemoirTemplate.objects.filter(price__lte=0).values_list('id', flat=True)
    return set(paid) | set(free)


def payment_error(e):
    return Response({'error': str(e)}, status=e.status)


class MemoirTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """Catalogue des modèles de mémoire.

    GET  /modeles/                      catalogue (+ owned, aperçu du plan)
    GET  /modeles/<slug>/               détail (plan complet si acheté)
    GET  /modeles/<slug>/cover/         page de garde d'exemple (HTML, filigrane si non acheté)
    POST /modeles/<slug>/purchase/      ouvre l'achat (mobile money ; sinon page Jɛmɛnipay → {checkout_url})
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
        if template.is_free:
            raise ValidationError({"error": "Ce modèle est gratuit : vous pouvez l'utiliser directement."})
        if template.is_owned_by(user):
            raise ValidationError({'error': 'Vous possédez déjà ce modèle.'})

        if mobile_money.is_enabled():
            purchase, created = mobile_money.open_purchase(user, template)
            return Response(TemplatePurchaseSerializer(purchase).data,
                            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

        pending = services.reusable_pending_purchase(user, template)
        if pending:
            return Response(TemplatePurchaseSerializer(pending).data)

        purchase = TemplatePurchase.objects.create(
            user=user, template=template, amount=template.price, currency=template.currency,
            provider=jemeni.provider(),
        )
        try:
            session = jemeni.create_checkout(
                amount=template.price,
                currency=template.currency,
                description=f'Modèle « {template.name} »',
                reference=f'MEMOAI-{purchase.id}',
                return_url=f'{settings.FRONTEND_URL}/modeles?achat={purchase.id}',
                metadata={'purchase_id': purchase.id, 'template': template.slug},
            )
        except jemeni.JemeniError as e:
            purchase.status = TemplatePurchase.FAILED
            purchase.save(update_fields=['status', 'updated_at'])
            return payment_error(e)

        purchase.checkout_session_id = session['id']
        purchase.checkout_url = session['checkout_url']
        purchase.transaction_reference = session['reference']
        purchase.save(update_fields=['checkout_session_id', 'checkout_url', 'transaction_reference', 'updated_at'])
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
    """Achats de l'utilisateur.

    POST /modeles/achats/<id>/declare/  annonce un paiement mobile money {operator, phone, reference}
    POST /modeles/achats/<id>/verify/   vérifie le paiement (message de l'opérateur, ou Jɛmɛnipay)
    """
    serializer_class = TemplatePurchaseSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = None

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return TemplatePurchase.objects.none()
        return TemplatePurchase.objects.filter(user=self.request.user).select_related('template')

    @action(detail=True, methods=['post'], throttle_scope='payment_declare')
    def declare(self, request, pk=None):
        purchase = self.get_object()
        try:
            mobile_money.declare(purchase, request.data.get('operator'), request.data.get('phone'),
                                 request.data.get('reference'))
        except mobile_money.PaymentError as e:
            raise ValidationError({'error': str(e)})
        return Response(self.get_serializer(purchase).data)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        purchase = self.get_object()
        if purchase.provider == mobile_money.PROVIDER:
            mobile_money.match_purchase(purchase)
            return Response(self.get_serializer(purchase).data)
        try:
            services.refresh_purchase(purchase)
        except jemeni.JemeniError as e:
            return payment_error(e)
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
def jemeni_webhook(request):
    """Webhook Jɛmɛnipay (payment.success / payment.failed), signé en HMAC-SHA512.
    Le contenu n'est jamais cru tel quel : l'achat est revérifié auprès de l'API."""
    if not jemeni.is_valid_webhook(request.body, request.headers.get('X-Jemeni-Signature', '')):
        return JsonResponse({'error': 'Signature invalide'}, status=401)
    try:
        payload = json.loads(request.body)
    except ValueError:
        return JsonResponse({'error': 'JSON invalide'}, status=400)
    data = payload.get('data') if isinstance(payload, dict) else None
    if not isinstance(data, dict) or not str(payload.get('event', '')).startswith('payment.'):
        return JsonResponse({'status': 'ignored'})

    transaction_id = str(data.get('transaction_id') or '')
    if not transaction_id:
        return JsonResponse({'status': 'ignored'})
    for purchase in TemplatePurchase.objects.filter(checkout_session_id=transaction_id):
        try:
            services.refresh_purchase(purchase)
        except jemeni.JemeniError:
            logger.warning("Webhook Jemeni : vérification impossible pour l'achat %s", purchase.id)
            return JsonResponse({'error': 'Vérification temporairement impossible'}, status=503)  # Jemeni réessaiera
    return JsonResponse({'status': 'ok'})
