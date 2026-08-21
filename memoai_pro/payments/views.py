import logging
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import stripe

from .models import Transaction
from projects.models import Project

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY

class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        project_id = request.data.get('project_id')
        project = Project.objects.get(id=project_id, user=request.user)
        # Créer une session Stripe
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': 'eur',
                            'product_data': {
                                'name': f"Export du mémoire: {project.title}",
                            },
                            'unit_amount': 2999,  # 29.99 €
                        },
                        'quantity': 1,
                    },
                ],
                mode='payment',
                success_url=settings.FRONTEND_URL + '/payment/success?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=settings.FRONTEND_URL + '/payment/cancel',
                metadata={'project_id': project_id, 'user_id': request.user.id}
            )
            # Créer une transaction en PENDING
            Transaction.objects.create(
                user=request.user,
                project=project,
                amount=29.99,
                currency='EUR',
                payment_method='stripe',
                status='PENDING',
                stripe_payment_intent_id=checkout_session.payment_intent,
                metadata={'session_id': checkout_session.id}
            )
            return Response({'sessionId': checkout_session.id, 'url': checkout_session.url})
        except Exception as e:
            return Response({'error': str(e)}, status=400)


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # Récupérer le project_id depuis metadata
        project_id = session['metadata']['project_id']
        try:
            transaction = Transaction.objects.get(stripe_payment_intent_id=session['payment_intent'])
            transaction.status = 'SUCCESS'
            transaction.save()
            # Débloquer l'export
            project = Project.objects.get(id=project_id)
            project.export_allowed = True
            project.save()
        except Transaction.DoesNotExist:
            logger.warning('Stripe webhook received for unknown transaction %s', session.get('payment_intent'))
        except Project.DoesNotExist:
            logger.warning('Stripe webhook failed to unlock non-existing project %s', project_id)
    return JsonResponse({'status': 'success'})