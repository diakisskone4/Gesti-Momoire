from django.urls import path
from rest_framework.routers import DefaultRouter

from .payment_views import AdminDeviceViewSet, AdminPaymentViewSet, DeviceMessagesView, PaymentOptionsView
from .views import MemoirTemplateViewSet, ProjectCoverView, TemplatePurchaseViewSet, jemeni_webhook

router = DefaultRouter()
router.register(r'achats', TemplatePurchaseViewSet, basename='template-purchase')
router.register(r'admin/paiements', AdminPaymentViewSet, basename='admin-payment')
router.register(r'admin/telephones', AdminDeviceViewSet, basename='admin-device')
router.register(r'', MemoirTemplateViewSet, basename='memoir-template')

urlpatterns = [
    path('paiement/', PaymentOptionsView.as_view(), name='payment-options'),
    path('paiement/messages/', DeviceMessagesView.as_view(), name='payment-messages'),
    path('webhook/jemeni/', jemeni_webhook, name='jemeni-webhook'),
    path('projects/<int:project_id>/cover/', ProjectCoverView.as_view(), name='project-cover'),
    *router.urls,
]
