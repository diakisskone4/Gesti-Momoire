import logging

import stripe
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.models import Project
from .models import Transaction

logger = logging.getLogger(__name__)

EXPORT_PRICE_CENTS = 2999  # 29,99 €


class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.STRIPE_SECRET_KEY:
            return Response({'error': "Le paiement en ligne n'est pas configuré (STRIPE_SECRET_KEY)."}, status=503)
        project = get_object_or_404(Project, id=request.data.get('project_id'), user=request.user)
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'eur',
                        'product_data': {'name': f"Export du mémoire : {project.title}"},
                        'unit_amount': EXPORT_PRICE_CENTS,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=settings.FRONTEND_URL + '/projects/%d/editor?payment=success' % project.id,
                cancel_url=settings.FRONTEND_URL + '/projects/%d/editor?payment=cancel' % project.id,
                metadata={'project_id': project.id, 'user_id': request.user.id},
            )
        except stripe.error.StripeError as e:
            logger.error('Stripe checkout error: %s', e)
            return Response({'error': 'Le paiement est momentanément indisponible.'}, status=502)

        Transaction.objects.create(
            user=request.user, project=project, amount=EXPORT_PRICE_CENTS / 100, currency='EUR',
            payment_method='stripe', status='PENDING',
            stripe_payment_intent_id=session.payment_intent or '',
            metadata={'session_id': session.id},
        )
        return Response({'sessionId': session.id, 'url': session.url})


@csrf_exempt
def stripe_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST attendu'}, status=405)
    if not settings.STRIPE_WEBHOOK_SECRET:
        return JsonResponse({'error': 'Webhook non configuré'}, status=503)
    try:
        event = stripe.Webhook.construct_event(
            request.body, request.META.get('HTTP_STRIPE_SIGNATURE'), settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # La transaction est retrouvée par l'identifiant de session (le payment_intent
        # peut être absent à la création de la session).
        transaction = Transaction.objects.filter(metadata__session_id=session['id']).first()
        if transaction is None:
            logger.warning('Stripe webhook: transaction inconnue pour la session %s', session['id'])
        else:
            transaction.status = 'SUCCESS'
            transaction.stripe_payment_intent_id = session.get('payment_intent') or transaction.stripe_payment_intent_id
            transaction.save(update_fields=['status', 'stripe_payment_intent_id', 'updated_at'])
            Project.objects.filter(id=transaction.project_id).update(export_allowed=True)
    return JsonResponse({'status': 'success'})
