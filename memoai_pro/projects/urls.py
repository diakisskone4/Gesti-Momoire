from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .images import ProjectImageUploadView, ProjectImageView
from .trash import TrashDeleteView, TrashEmptyView, TrashRestoreView, TrashView
from .views import ProjectViewSet, ChapterViewSet, FolderViewSet, ReferenceViewSet

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'chapters', ChapterViewSet, basename='chapter')
router.register(r'folders', FolderViewSet, basename='folder')
router.register(r'references', ReferenceViewSet, basename='reference')

urlpatterns = [
    path('images/', ProjectImageUploadView.as_view(), name='project-image-upload'),
    path('images/<int:pk>/', ProjectImageView.as_view(), name='project-image'),
    path('trash/', TrashView.as_view(), name='trash'),
    path('trash/restore/', TrashRestoreView.as_view(), name='trash-restore'),
    path('trash/delete/', TrashDeleteView.as_view(), name='trash-delete'),
    path('trash/empty/', TrashEmptyView.as_view(), name='trash-empty'),
    path('', include(router.urls)),
]