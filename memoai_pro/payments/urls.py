from django.urls import path

from .views import CreateCheckoutSessionView, stripe_webhook

urlpatterns = [
    path('checkout/', CreateCheckoutSessionView.as_view(), name='payments_checkout'),
    path('webhook/', stripe_webhook, name='payments_webhook'),
]
