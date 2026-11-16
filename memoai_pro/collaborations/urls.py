from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CommentViewSet, 
    ValidationViewSet, 
    CollaboratorViewSet, 
    ShareLinkViewSet,
    SharedProjectView,
)

router = DefaultRouter()
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'validations', ValidationViewSet, basename='validation')
router.register(r'collaborators', CollaboratorViewSet, basename='collaborator')
router.register(r'share-links', ShareLinkViewSet, basename='share-link')

urlpatterns = [
    path('shared/<str:token>/', SharedProjectView.as_view(), name='shared-project'),
    path('', include(router.urls)),
]