import logging
import re
from html import escape
from io import BytesIO

import requests
from django.db import models
from django.db.models import Q
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from .trash import move_to_trash
from .access import get_owned_project, is_reviewer, readable_project_q
from .models import Chapter, Folder, Project, Reference
from .serializers import ChapterSerializer, FolderSerializer, ProjectSerializer, ReferenceSerializer

logger = logging.getLogger(__name__)

try:
    from docx import Document
except ImportError:  # pragma: no cover
    Document = None

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
except ImportError:  # pragma: no cover
    SimpleDocTemplate = None


def safe_filename(title, ext):
    name = re.sub(r'[^\w\- ]+', '', title or 'memoire', flags=re.UNICODE).strip() or 'memoire'
    return f'{name[:80]}.{ext}'


def format_reference(ref):
    parts = [f'{ref.authors} ({ref.year}). {ref.title}.']
    if ref.journal:
        parts.append(f'{ref.journal}.')
    if ref.doi:
        parts.append(f'https://doi.org/{ref.doi}')
    return ' '.join(parts)


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Chaque rôle voit les mémoires qui le concernent :
        - étudiant : les siens ;
        - encadreur / co-encadreur : ceux qu'il encadre (+ les siens) ;
        - jury : ceux dont il est membre du jury ;
        - administrateur : tous.
        Le paramètre ?scope=mine|supervised|jury restreint la liste."""
        if getattr(self, 'swagger_fake_view', False):  # génération du schéma Swagger
            return Project.objects.none()
        user = self.request.user
        qs = Project.objects.select_related('user', 'supervisor', 'co_supervisor').prefetch_related(
            'jury', 'chapters__children',
        )
        if user.role != 'ADMIN':
            qs = qs.filter(
                Q(user=user) | Q(supervisor=user) | Q(co_supervisor=user) | Q(jury=user)
            ).distinct()

        scope = self.request.query_params.get('scope')
        if scope == 'mine':
            qs = qs.filter(user=user)
            if self.request.query_params.get('archived') != '1':
                qs = qs.exclude(status='ARCHIVED')
        elif scope == 'supervised':
            qs = qs.filter(Q(supervisor=user) | Q(co_supervisor=user))
        elif scope == 'jury':
            qs = qs.filter(jury=user)
        return qs.order_by('-updated_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def _require_owner(self, project):
        if project.user_id != self.request.user.id:
            raise PermissionDenied("Seul l'auteur du mémoire peut effectuer cette action.")

    def perform_update(self, serializer):
        self._require_owner(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user_id != self.request.user.id and self.request.user.role != 'ADMIN':
            raise PermissionDenied("Seul l'auteur du mémoire peut le supprimer.")
        move_to_trash(instance)  # restaurable depuis la corbeille pendant 30 jours

    # ---------------------------------------------------------- cycle de vie

    @action(detail=True, methods=['post'])
    def submit_review(self, request, pk=None):
        """Étudiant : soumet le mémoire à son encadreur (→ En relecture)."""
        project = self.get_object()
        self._require_owner(project)
        if project.status not in ('DRAFT', 'IN_PROGRESS'):
            raise ValidationError({'error': 'Ce mémoire ne peut pas être soumis dans son état actuel.'})
        if not project.supervisor_id and not project.co_supervisor_id:
            raise ValidationError({'error': "Ajoutez d'abord un encadreur à votre mémoire."})
        project.status = 'REVIEW'
        project.submitted_at = timezone.now()
        project.save(update_fields=['status', 'submitted_at', 'updated_at'])
        from notifications.signals import notify
        for reviewer in (project.supervisor, project.co_supervisor):
            if reviewer:
                notify(reviewer, request.user, 'a soumis son mémoire pour relecture', project, project.title)
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Encadreur / co-encadreur / jury : valide ou demande des corrections.
        Corps : {"decision": "approve" | "request_changes", "comment": "..."}"""
        project = self.get_object()
        user = request.user
        if not is_reviewer(project, user):
            raise PermissionDenied("Vous n'êtes ni encadreur ni membre du jury de ce mémoire.")
        if project.status != 'REVIEW':
            raise ValidationError({'error': "Ce mémoire n'est pas en relecture."})

        decision = request.data.get('decision')
        comment = str(request.data.get('comment') or '')
        if decision == 'approve':
            project.status = 'VALIDATED'
            project.validated_at = timezone.now()
        elif decision == 'request_changes':
            if not comment.strip():
                raise ValidationError({'comment': 'Expliquez les corrections attendues.'})
            project.status = 'IN_PROGRESS'
        else:
            raise ValidationError({'decision': 'Valeur attendue : approve ou request_changes.'})
        project.review_comment = comment
        project.save(update_fields=['status', 'validated_at', 'review_comment', 'updated_at'])

        from notifications.signals import notify
        verb = 'a validé votre mémoire' if decision == 'approve' else 'demande des corrections sur votre mémoire'
        notify(project.user, user, verb, project, comment or project.title)
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        project = self.get_object()
        self._require_owner(project)
        if project.status != 'ARCHIVED':
            project.status_before_archive = project.status
            project.status = 'ARCHIVED'
            project.archived_at = timezone.now()
            project.save(update_fields=['status', 'status_before_archive', 'archived_at', 'updated_at'])
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        project = self.get_object()
        self._require_owner(project)
        if project.status == 'ARCHIVED':
            project.status = project.status_before_archive or 'IN_PROGRESS'
            project.archived_at = None
            project.save(update_fields=['status', 'archived_at', 'updated_at'])
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=['post'])
    def generate_plan(self, request, pk=None):
        project = self.get_object()
        self._require_owner(project)
        from ai.views import plan_generation_response
        return plan_generation_response(project)

    # ---------------------------------------------------------- export

    @action(detail=True, methods=['post'])
    def request_export(self, request, pk=None):
        project = self.get_object()
        if not project.export_allowed:
            return Response({'error': 'Export non autorisé. Veuillez payer.'}, status=status.HTTP_402_PAYMENT_REQUIRED)
        from exports.tasks import export_project_task
        task = export_project_task.delay(project.id, request.data.get('format', 'docx'))
        return Response({'task_id': task.id})

    @action(detail=True, methods=['post'])
    def export(self, request, pk=None):
        project = self.get_object()
        if not project.export_allowed:
            return Response({'error': 'Export non autorisé. Veuillez payer.'}, status=status.HTTP_402_PAYMENT_REQUIRED)
        format_type = request.data.get('format', 'docx')
        include_chapters = bool(request.data.get('include_chapters', True))
        include_bibliography = bool(request.data.get('include_bibliography', True))

        exporters = {'docx': self.export_docx, 'pdf': self.export_pdf, 'html': self.export_html}
        if format_type not in exporters:
            return Response({'error': 'Format non supporté (docx, pdf ou html).'}, status=status.HTTP_400_BAD_REQUEST)
        if format_type == 'docx' and Document is None:
            return Response({'error': "Le module python-docx n'est pas installé."}, status=500)
        if format_type == 'pdf' and SimpleDocTemplate is None:
            return Response({'error': "Le module reportlab n'est pas installé."}, status=500)
        return exporters[format_type](project, include_chapters, include_bibliography)

    @staticmethod
    def _outline(project):
        """Chapitres puis leurs sections, dans l'ordre : [(niveau, chapitre), ...]."""
        items = []

        def walk(nodes, level):
            for node in nodes:
                items.append((level, node))
                walk(node.children.all().order_by('order'), level + 1)

        walk(project.chapters.filter(parent=None).order_by('order'), 1)
        return items

    @staticmethod
    def _cover(project):
        """(modèle, données) de la page de garde si le mémoire utilise un modèle acheté, sinon None."""
        template = project.template
        if template is None or not template.is_owned_by(project.user):
            return None
        from modeles.covers import cover_data
        return template, cover_data(template, project)

    def _meta_lines(self, project):
        author = project.user.full_name
        return [
            f'Auteur : {author}',
            f'Niveau : {project.get_level_display()}',
            f"Université : {project.university or 'Non spécifiée'}",
            f"Thème : {project.theme or 'Non spécifié'}",
        ]

    def _export_data(self, project, include_chapters, include_bibliography):
        """Contenu à imprimer : plan numéroté, références, page de garde, images des figures."""
        from . import memoir_export
        outline = self._outline(project) if include_chapters else []
        refs = project.references.all().order_by('authors', 'year') if include_bibliography else []
        cover = self._cover(project)
        cover_lines = None
        if cover:
            from modeles.covers import cover_lines as make_cover_lines
            cover_lines = make_cover_lines(cover[1])
        ids = memoir_export.figure_ids(outline)
        images = {image.id: image for image in project.images.filter(id__in=ids)} if ids else {}
        return memoir_export.ExportData(
            project=project, parts=memoir_export.build_layout(outline),
            references=[format_reference(r) for r in refs], cover_lines=cover_lines,
            meta_lines=self._meta_lines(project), images=images,
        )

    def export_docx(self, project, include_chapters, include_bibliography):
        """Word présenté comme un mémoire imprimé (voir projects/memoir_export.py)."""
        from . import memoir_export
        data = memoir_export.render_docx(self._export_data(project, include_chapters, include_bibliography))
        return FileResponse(
            BytesIO(data), as_attachment=True, filename=safe_filename(project.title, 'docx'),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )

    def export_pdf(self, project, include_chapters, include_bibliography):
        """PDF présenté comme un mémoire imprimé (voir projects/memoir_export.py)."""
        from . import memoir_export
        data = memoir_export.render_pdf(self._export_data(project, include_chapters, include_bibliography))
        return FileResponse(BytesIO(data), as_attachment=True, filename=safe_filename(project.title, 'pdf'),
                            content_type='application/pdf')

    def export_html(self, project, include_chapters, include_bibliography):
        """HTML imprimable aux mêmes normes."""
        from . import memoir_export
        cover_css = cover_html = ''
        cover = self._cover(project)
        if cover:
            from modeles.covers import render_cover_parts
            cover_css, cover_html = render_cover_parts(*cover)
            cover_css += '.page{margin:0 auto 40px;box-shadow:0 2px 12px #0002;page-break-after:always}'
        html = memoir_export.render_html(self._export_data(project, include_chapters, include_bibliography),
                                         cover_css, cover_html)
        response = HttpResponse(html, content_type='text/html; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{safe_filename(project.title, "html")}"'
        return response


class ChapterViewSet(viewsets.ModelViewSet):
    """Lecture : l'auteur, ses encadreurs et son jury. Écriture : l'auteur seul."""
    serializer_class = ChapterSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = None  # « ai » pour la rédaction automatique (voir generate_content)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # génération du schéma Swagger
            return Chapter.objects.none()
        user = self.request.user
        queryset = Chapter.objects.filter(readable_project_q(user)).distinct()
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset.select_related('project').order_by('order', 'id')

    def _require_owner(self, chapter):
        if chapter.project.user_id != self.request.user.id:
            raise PermissionDenied("Seul l'auteur du mémoire peut modifier ses chapitres.")

    def perform_create(self, serializer):
        project_id = self.request.data.get('project')
        if not project_id:
            raise ValidationError({'project': 'Le champ project est requis.'})
        project = get_owned_project(self.request.user, project_id)
        parent = serializer.validated_data.get('parent')
        if parent and parent.project_id != project.id:
            raise ValidationError({'parent': 'Le chapitre parent appartient à un autre mémoire.'})
        serializer.save(project=project)

    def perform_update(self, serializer):
        self._require_owner(serializer.instance)
        if 'content' in serializer.validated_data and serializer.validated_data['content'] != serializer.instance.content:
            serializer.save(version=serializer.instance.version + 1)
        else:
            serializer.save()

    def perform_destroy(self, instance):
        self._require_owner(instance)
        move_to_trash(instance)  # restaurable depuis la corbeille pendant 30 jours

    @action(detail=True, methods=['post'], throttle_scope='ai')
    def generate_content(self, request, pk=None):
        """Rédige par IA l'introduction et les sections vides d'un chapitre (modèle acheté requis)."""
        chapter = self.get_object()
        self._require_owner(chapter)
        from ai.generation import write_chapter_content
        from ai.services import AIError
        try:
            written = write_chapter_content(chapter.project, chapter)
        except AIError as e:
            return Response({'error': str(e)}, status=e.status)
        chapters = Chapter.objects.filter(project=chapter.project).order_by('order', 'id')
        return Response({'written': written, 'chapters': ChapterSerializer(chapters, many=True).data})

    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None):
        chapter = self.get_object()
        self._require_owner(chapter)
        try:
            new_order = int(request.data.get('order'))
        except (TypeError, ValueError):
            return Response({'error': 'order (entier) requis'}, status=status.HTTP_400_BAD_REQUEST)
        siblings = Chapter.objects.filter(project=chapter.project, parent=chapter.parent).exclude(id=chapter.id)
        if new_order > chapter.order:
            siblings.filter(order__gt=chapter.order, order__lte=new_order).update(order=models.F('order') - 1)
        else:
            siblings.filter(order__gte=new_order, order__lt=chapter.order).update(order=models.F('order') + 1)
        chapter.order = new_order
        chapter.save(update_fields=['order', 'updated_at'])
        return Response({'status': 'reordered'})


class FolderViewSet(viewsets.ModelViewSet):
    serializer_class = FolderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # génération du schéma Swagger
            return Folder.objects.none()
        return Folder.objects.filter(user=self.request.user, parent=None)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ReferenceViewSet(viewsets.ModelViewSet):
    """Bibliographie d'un mémoire : ?project_id=<id>. Lecture pour l'encadrement, écriture pour l'auteur."""
    serializer_class = ReferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # génération du schéma Swagger
            return Reference.objects.none()
        qs = Reference.objects.filter(readable_project_q(self.request.user)).distinct()
        project_id = self.request.query_params.get('project_id')
        if project_id:
            qs = qs.filter(project_id=project_id)
        elif self.action == 'list':
            return Reference.objects.none()
        return qs.order_by('authors', 'year')

    def _require_owner(self, project):
        if project.user_id != self.request.user.id:
            raise PermissionDenied("Seul l'auteur du mémoire peut modifier sa bibliographie.")

    def perform_create(self, serializer):
        self._require_owner(serializer.validated_data['project'])
        serializer.save()

    def perform_update(self, serializer):
        self._require_owner(serializer.instance.project)
        if 'project' in serializer.validated_data:
            self._require_owner(serializer.validated_data['project'])
        serializer.save(bibtex=None)

    def perform_destroy(self, instance):
        self._require_owner(instance.project)
        move_to_trash(instance)  # restaurable depuis la corbeille pendant 30 jours

    @action(detail=True, methods=['get'])
    def bibtex(self, request, pk=None):
        ref = self.get_object()
        if not ref.bibtex:
            first_author = re.sub(r'\W+', '', (ref.authors.split(',')[0].split(' ')[0] or 'ref'))
            fields = [f'  title = {{{ref.title}}}', f'  author = {{{ref.authors}}}', f'  year = {{{ref.year}}}']
            if ref.journal:
                fields.append(f'  journal = {{{ref.journal}}}')
            if ref.doi:
                fields.append(f'  doi = {{{ref.doi}}}')
            if ref.isbn:
                fields.append(f'  isbn = {{{ref.isbn}}}')
            ref.bibtex = '@article{%s%s,\n%s\n}' % (first_author.lower(), ref.year, ',\n'.join(fields))
            ref.save(update_fields=['bibtex'])
        return Response({'bibtex': ref.bibtex})

    @action(detail=False, methods=['post'])
    def import_by_doi(self, request):
        doi = str(request.data.get('doi') or '').strip()
        doi = re.sub(r'^(https?://(dx\.)?doi\.org/|doi:)', '', doi, flags=re.I)
        if not re.match(r'^10\.\d{4,9}/\S+$', doi):
            raise ValidationError({'error': 'DOI invalide (ex. 10.1038/nature12373).'})
        project = get_owned_project(request.user, request.data.get('project_id'))
        try:
            response = requests.get(f'https://api.crossref.org/works/{doi}', timeout=10)
        except requests.RequestException:
            return Response({'error': 'Service Crossref injoignable. Réessayez plus tard.'}, status=502)
        if response.status_code != 200:
            return Response({'error': 'DOI introuvable.'}, status=404)

        data = response.json().get('message', {})
        date_parts = (data.get('issued') or {}).get('date-parts') or [[None]]
        year = date_parts[0][0] if date_parts and date_parts[0] else None
        ref = Reference.objects.create(
            project=project,
            title=((data.get('title') or ['Sans titre'])[0])[:500],
            authors=(', '.join(
                f"{a.get('family', '')} {a.get('given', '')}".strip() for a in data.get('author', [])
            ) or 'Auteur inconnu')[:500],
            year=year or timezone.now().year,
            doi=doi[:255],
            journal=((data.get('container-title') or [''])[0])[:255],
        )
        return Response(ReferenceSerializer(ref).data, status=status.HTTP_201_CREATED)
