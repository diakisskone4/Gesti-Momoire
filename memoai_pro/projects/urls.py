from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .images import ProjectImageUploadView, ProjectImageView
from .views import ProjectViewSet, ChapterViewSet, FolderViewSet, ReferenceViewSet

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'chapters', ChapterViewSet, basename='chapter')
router.register(r'folders', FolderViewSet, basename='folder')
router.register(r'references', ReferenceViewSet, basename='reference')

urlpatterns = [
    path('images/', ProjectImageUploadView.as_view(), name='project-image-upload'),
    path('images/<int:pk>/', ProjectImageView.as_view(), name='project-image'),
    path('', include(router.urls)),
]