from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from .models import Comment, Validation, Collaborator, ShareLink
from .serializers import (
    CommentSerializer, 
    ValidationSerializer, 
    CollaboratorSerializer, 
    ShareLinkSerializer
)
from users.permissions import IsProjectOwnerOrSupervisor
from projects.models import Project
import secrets

User = get_user_model()


class CommentViewSet(viewsets.ModelViewSet):
    """ViewSet pour les commentaires"""
    
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectOwnerOrSupervisor]

    def get_queryset(self):
        project_id = self.request.query_params.get('project_id')
        chapter_id = self.request.query_params.get('chapter_id')
        
        queryset = Comment.objects.filter(parent=None)
        
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if chapter_id:
            queryset = queryset.filter(chapter_id=chapter_id)
        
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        comment = self.get_object()
        comment.resolved = True
        comment.save()
        return Response({'status': 'resolved'})

    @action(detail=True, methods=['post'])
    def unresolve(self, request, pk=None):
        comment = self.get_object()
        comment.resolved = False
        comment.save()
        return Response({'status': 'unresolved'})


class ValidationViewSet(viewsets.ModelViewSet):
    """ViewSet pour les validations"""
    
    serializer_class = ValidationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        project_id = self.request.query_params.get('project_id')
        
        queryset = Validation.objects.filter(validator=user)
        
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        return queryset

    def perform_create(self, serializer):
        # Vérifier que l'utilisateur est bien encadreur ou jury
        if self.request.user.role not in ['SUPERVISOR', 'CO_SUPERVISOR', 'JURY']:
            raise permissions.PermissionDenied("Seul un encadreur ou un jury peut valider.")
        serializer.save(validator=self.request.user)


class CollaboratorViewSet(viewsets.ModelViewSet):
    """ViewSet pour les collaborateurs"""
    
    serializer_class = CollaboratorSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        project_id = self.request.query_params.get('project')
        
        if project_id:
            # Retourner les collaborateurs du projet (si l'utilisateur y a accès)
            return Collaborator.objects.filter(
                project_id=project_id,
                project__user=user
            ) | Collaborator.objects.filter(
                project_id=project_id,
                user=user
            )
        
        return Collaborator.objects.filter(project__user=user)
    
    def create(self, request, *args, **kwargs):
        project_id = request.data.get('project')
        email = request.data.get('email')
        role = request.data.get('role', 'viewer')
        
        if not project_id or not email:
            return Response(
                {'error': 'Project et email requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        project = get_object_or_404(Project, id=project_id, user=request.user)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'Utilisateur non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if Collaborator.objects.filter(project=project, user=user).exists():
            return Response(
                {'error': 'Cet utilisateur est déjà collaborateur'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        permissions = {
            'can_edit': role == 'editor',
            'can_comment': True,
            'can_export': True,
            'can_share': role == 'owner'
        }
        
        collaborator = Collaborator.objects.create(
            project=project,
            user=user,
            role=role,
            status='active',
            **permissions
        )
        
        serializer = self.get_serializer(collaborator)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.project.user != request.user and instance.user != request.user:
            return Response(
                {'error': 'Permission refusée'},
                status=status.HTTP_403_FORBIDDEN
            )
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ShareLinkViewSet(viewsets.ModelViewSet):
    """ViewSet pour les liens de partage"""
    
    serializer_class = ShareLinkSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        project_id = self.request.query_params.get('project')
        if project_id:
            return ShareLink.objects.filter(project_id=project_id, project__user=self.request.user)
        return ShareLink.objects.none()
    
    def create(self, request, *args, **kwargs):
        project_id = request.data.get('project')
        permissions = request.data.get('permissions', {})
        
        if not project_id:
            return Response(
                {'error': 'Project requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        project = get_object_or_404(Project, id=project_id, user=request.user)
        
        token = secrets.token_urlsafe(32)
        
        share_link = ShareLink.objects.create(
            project=project,
            token=token,
            can_edit=permissions.get('can_edit', False),
            can_comment=permissions.get('can_comment', True),
            can_export=permissions.get('can_export', True)
        )
        
        serializer = self.get_serializer(share_link)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['post'])
    def revoke_all(self, request):
        project_id = request.data.get('project')
        if not project_id:
            return Response(
                {'error': 'Project requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ShareLink.objects.filter(project_id=project_id, project__user=request.user).delete()
        return Response({'message': 'Tous les liens ont été révoqués'})