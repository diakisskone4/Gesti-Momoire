from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet, ChapterViewSet, FolderViewSet, ReferenceViewSet

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'chapters', ChapterViewSet, basename='chapter')
router.register(r'folders', FolderViewSet, basename='folder')
router.register(r'references', ReferenceViewSet, basename='reference')

urlpatterns = [
    path('', include(router.urls)),
]