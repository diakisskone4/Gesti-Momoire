import secrets

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.access import can_read, get_owned_project, is_reviewer, readable_project_q
from .models import Collaborator, Comment, ShareLink, Validation
from .serializers import CollaboratorSerializer, CommentSerializer, ShareLinkSerializer, ValidationSerializer

User = get_user_model()


class CommentViewSet(viewsets.ModelViewSet):
    """Commentaires sur un mémoire ou un chapitre : ?project_id= ou ?chapter_id=.
    Visibles et rédigeables par toute personne ayant accès au mémoire."""
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # génération du schéma Swagger
            return Comment.objects.none()
        user = self.request.user
        qs = Comment.objects.filter(
            readable_project_q(user) | readable_project_q(user, 'chapter__project__')
        ).distinct().select_related('user')
        if self.action == 'list':
            qs = qs.filter(parent=None)
            project_id = self.request.query_params.get('project_id')
            chapter_id = self.request.query_params.get('chapter_id')
            if project_id:
                qs = qs.filter(project_id=project_id)
            if chapter_id:
                qs = qs.filter(chapter_id=chapter_id)
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        data = serializer.validated_data
        chapter, parent = data.get('chapter'), data.get('parent')
        project = data.get('project') or (chapter.project if chapter else None) or (parent.project if parent else None)
        if project is None:
            raise ValidationError({'project': 'Indiquez le mémoire ou le chapitre commenté.'})
        if chapter and chapter.project_id != project.id:
            raise ValidationError({'chapter': "Ce chapitre n'appartient pas à ce mémoire."})
        if not can_read(project, self.request.user):
            raise PermissionDenied("Vous n'avez pas accès à ce mémoire.")
        serializer.save(user=self.request.user, project=project)

    def _require_author(self, comment):
        if comment.user_id != self.request.user.id:
            raise PermissionDenied('Vous ne pouvez modifier que vos propres commentaires.')

    def perform_update(self, serializer):
        self._require_author(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user_id != self.request.user.id and instance.project and instance.project.user_id != self.request.user.id:
            raise PermissionDenied('Vous ne pouvez supprimer que vos propres commentaires.')
        instance.delete()

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        comment = self.get_object()
        comment.resolved = True
        comment.save(update_fields=['resolved', 'updated_at'])
        return Response({'status': 'resolved'})

    @action(detail=True, methods=['post'])
    def unresolve(self, request, pk=None):
        comment = self.get_object()
        comment.resolved = False
        comment.save(update_fields=['resolved', 'updated_at'])
        return Response({'status': 'unresolved'})


class ValidationViewSet(viewsets.ModelViewSet):
    """Validation de chapitres par l'encadrement ou le jury du mémoire."""
    serializer_class = ValidationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # génération du schéma Swagger
            return Validation.objects.none()
        user = self.request.user
        qs = Validation.objects.filter(readable_project_q(user)).distinct().select_related('validator')
        project_id = self.request.query_params.get('project_id')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    def perform_create(self, serializer):
        project = serializer.validated_data['project']
        chapter = serializer.validated_data.get('chapter')
        if not is_reviewer(project, self.request.user):
            raise PermissionDenied("Seul l'encadrement ou le jury de ce mémoire peut valider.")
        if chapter and chapter.project_id != project.id:
            raise ValidationError({'chapter': "Ce chapitre n'appartient pas à ce mémoire."})
        if chapter and Validation.objects.filter(chapter=chapter, validator=self.request.user).exists():
            raise ValidationError({'chapter': 'Vous avez déjà validé ce chapitre : modifiez votre validation.'})
        serializer.save(validator=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.validator_id != self.request.user.id:
            raise PermissionDenied('Vous ne pouvez modifier que vos propres validations.')
        serializer.save()

    def perform_destroy(self, instance):
        if instance.validator_id != self.request.user.id:
            raise PermissionDenied('Vous ne pouvez supprimer que vos propres validations.')
        instance.delete()


class CollaboratorViewSet(viewsets.ModelViewSet):
    """Collaborateurs d'un mémoire (?project=<id>). Gérés par l'auteur."""
    serializer_class = CollaboratorSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # génération du schéma Swagger
            return Collaborator.objects.none()
        user = self.request.user
        qs = (Collaborator.objects.filter(project__user=user) | Collaborator.objects.filter(user=user)).select_related('user')
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs.distinct()

    def create(self, request, *args, **kwargs):
        email = str(request.data.get('email') or '').strip().lower()
        role = request.data.get('role', 'viewer')
        if not email:
            raise ValidationError({'error': 'Email requis.'})
        if role not in ('viewer', 'editor'):
            raise ValidationError({'error': 'Rôle invalide (viewer ou editor).'})
        project = get_owned_project(request.user, request.data.get('project'))

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            return Response({'error': "Aucun compte MemoAI n'utilise cet email."}, status=status.HTTP_404_NOT_FOUND)
        if user == request.user:
            raise ValidationError({'error': 'Vous êtes déjà l\'auteur de ce mémoire.'})
        if Collaborator.objects.filter(project=project, user=user).exists():
            raise ValidationError({'error': 'Cet utilisateur est déjà collaborateur.'})

        collaborator = Collaborator.objects.create(
            project=project, user=user, role=role, status='active',
            can_edit=role == 'editor', can_comment=True, can_export=True, can_share=False,
        )
        from notifications.signals import notify
        notify(user, request.user, 'vous a ajouté comme collaborateur', project, project.title)
        return Response(self.get_serializer(collaborator).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        if serializer.instance.project.user_id != self.request.user.id:
            raise PermissionDenied("Seul l'auteur du mémoire gère ses collaborateurs.")
        role = serializer.validated_data.get('role')
        if role == 'owner':
            raise ValidationError({'role': "Le rôle propriétaire n'est pas transférable."})
        extra = {'can_edit': role == 'editor'} if role else {}
        serializer.save(**extra)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.project.user_id != request.user.id and instance.user_id != request.user.id:
            raise PermissionDenied('Permission refusée.')
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ShareLinkViewSet(viewsets.ModelViewSet):
    """Liens de partage en lecture d'un mémoire (?project=<id>). Gérés par l'auteur."""
    serializer_class = ShareLinkSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'token'
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # génération du schéma Swagger
            return ShareLink.objects.none()
        qs = ShareLink.objects.filter(project__user=self.request.user)
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        elif self.action == 'list':
            return ShareLink.objects.none()
        return qs.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        project = get_owned_project(request.user, request.data.get('project'))
        perms = request.data.get('permissions') or {}
        share_link = ShareLink.objects.create(
            project=project,
            token=secrets.token_urlsafe(32),
            can_edit=False,
            can_comment=bool(perms.get('can_comment', True)),
            can_export=bool(perms.get('can_export', False)),
        )
        return Response(self.get_serializer(share_link).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def revoke_all(self, request):
        project = get_owned_project(request.user, request.data.get('project'))
        deleted, _ = ShareLink.objects.filter(project=project).delete()
        return Response({'message': 'Tous les liens ont été révoqués', 'deleted': deleted})


class SharedProjectView(APIView):
    """Lecture publique d'un mémoire via un lien de partage : GET /projects/shared/<token>/."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_scope = 'shared'

    def get(self, request, token):
        link = ShareLink.objects.select_related('project__user').filter(token=token).first()
        if link is None or (link.expires_at and link.expires_at < timezone.now()) or link.project.deleted_at:
            return Response({'error': 'Ce lien de partage est invalide ou a expiré.'}, status=status.HTTP_404_NOT_FOUND)
        project = link.project

        def tree(parent):
            return [
                {'id': c.id, 'title': c.title, 'content': c.content or '', 'children': tree(c)}
                for c in project.chapters.filter(parent=parent).order_by('order', 'id')
            ]

        return Response({
            'title': project.title,
            'theme': project.theme,
            'level': project.get_level_display(),
            'university': project.university,
            'academic_year': project.academic_year,
            'author': project.user.full_name,
            'status_label': project.get_status_display(),
            'chapters': tree(None),
            'references': [
                {'authors': r.authors, 'year': r.year, 'title': r.title, 'journal': r.journal, 'doi': r.doi}
                for r in project.references.order_by('authors', 'year')
            ],
        })
