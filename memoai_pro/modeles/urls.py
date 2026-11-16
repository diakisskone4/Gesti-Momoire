from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import MemoirTemplateViewSet, ProjectCoverView, TemplatePurchaseViewSet, saspay_webhook

router = DefaultRouter()
router.register(r'achats', TemplatePurchaseViewSet, basename='template-purchase')
router.register(r'', MemoirTemplateViewSet, basename='memoir-template')

urlpatterns = [
    path('webhook/saspay/', saspay_webhook, name='saspay-webhook'),
    path('projects/<int:project_id>/cover/', ProjectCoverView.as_view(), name='project-cover'),
    *router.urls,
]
