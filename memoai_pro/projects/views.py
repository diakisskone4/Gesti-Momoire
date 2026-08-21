from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from .models import Project, Folder, Chapter, Reference
from .serializers import ProjectSerializer, FolderSerializer, ChapterSerializer, ReferenceSerializer
from users.permissions import IsProjectOwnerOrSupervisor
from ai.tasks import generate_plan_task
from io import BytesIO
import requests

# Import conditionnel pour éviter les erreurs si les modules ne sont pas installés
try:
    import docx
    from docx import Document
except ImportError:
    docx = None
    Document = None

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    letter = None
    canvas = None


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user).order_by('-updated_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def generate_plan(self, request, pk=None):
        project = self.get_object()
        if project.status != 'DRAFT':
            return Response({'error': 'Plan déjà généré'}, status=status.HTTP_400_BAD_REQUEST)
        
        from ai.models import AIGenerationTask
        task = generate_plan_task.delay(project.id, project.theme)
        ai_task = AIGenerationTask.objects.create(
            project=project,
            type='plan',
            status='PENDING',
            celery_task_id=task.id
        )
        return Response({'task_id': task.id, 'ai_task_id': ai_task.id})

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
        format_type = request.data.get('format', 'docx')
        include_chapters = request.data.get('include_chapters', True)
        include_bibliography = request.data.get('include_bibliography', True)

        if format_type == 'docx':
            if Document is None:
                return Response(
                    {'error': 'Le module python-docx n\'est pas installé. Installez-le avec: pip install python-docx'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            return self.export_docx(project, include_chapters, include_bibliography)
        elif format_type == 'pdf':
            if canvas is None:
                return Response(
                    {'error': 'Le module reportlab n\'est pas installé. Installez-le avec: pip install reportlab'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            return self.export_pdf(project, include_chapters, include_bibliography)
        elif format_type == 'html':
            return self.export_html(project, include_chapters, include_bibliography)
        else:
            return Response(
                {'error': 'Format non supporté'},
                status=status.HTTP_400_BAD_REQUEST
            )

    def export_docx(self, project, include_chapters, include_bibliography):
        doc = Document()
        
        doc.add_heading(project.title, 0)
        doc.add_paragraph(f"Theme: {project.theme or 'Non spécifié'}")
        doc.add_paragraph(f"Niveau: {project.level}")
        doc.add_paragraph(f"Université: {project.university or 'Non spécifiée'}")
        doc.add_paragraph("\n" + "="*50 + "\n")
        
        if include_chapters:
            chapters = Chapter.objects.filter(project=project).order_by('order')
            for chapter in chapters:
                doc.add_heading(chapter.title, level=1)
                doc.add_paragraph(chapter.content or '')
                doc.add_paragraph("\n")
        
        if include_bibliography:
            doc.add_heading("Bibliographie", level=1)
            references = Reference.objects.filter(project=project)
            for ref in references:
                doc.add_paragraph(
                    f"{ref.authors} ({ref.year}). {ref.title}. "
                    f"{ref.journal or 'Éditeur inconnu'}."
                )
        
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=f"{project.title}.docx",
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    def export_pdf(self, project, include_chapters, include_bibliography):
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        y = 750
        
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, project.title)
        y -= 30
        
        c.setFont("Helvetica", 12)
        c.drawString(50, y, f"Theme: {project.theme or 'Non spécifié'}")
        y -= 20
        c.drawString(50, y, f"Niveau: {project.level}")
        y -= 20
        c.drawString(50, y, f"Université: {project.university or 'Non spécifiée'}")
        y -= 30
        
        if include_chapters:
            chapters = Chapter.objects.filter(project=project).order_by('order')
            for chapter in chapters:
                if y < 50:
                    c.showPage()
                    y = 750
                c.setFont("Helvetica-Bold", 14)
                c.drawString(50, y, chapter.title)
                y -= 20
                c.setFont("Helvetica", 11)
                content = chapter.content[:500] if chapter.content else ''
                lines = content.split('\n')
                for line in lines:
                    if y < 50:
                        c.showPage()
                        y = 750
                    c.drawString(50, y, line[:80])
                    y -= 15
                y -= 20
        
        c.save()
        buffer.seek(0)
        
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=f"{project.title}.pdf",
            content_type='application/pdf'
        )

    def export_html(self, project, include_chapters, include_bibliography):
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{project.title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #0f766e; }}
                .chapter {{ margin: 20px 0; }}
                .chapter-title {{ color: #173e3a; }}
                .reference {{ margin: 5px 0; }}
            </style>
        </head>
        <body>
            <h1>{project.title}</h1>
            <p><strong>Theme:</strong> {project.theme or 'Non spécifié'}</p>
            <p><strong>Niveau:</strong> {project.level}</p>
            <p><strong>Université:</strong> {project.university or 'Non spécifiée'}</p>
            <hr>
        """
        
        if include_chapters:
            chapters = Chapter.objects.filter(project=project).order_by('order')
            for chapter in chapters:
                html += f"""
                <div class="chapter">
                    <h2 class="chapter-title">{chapter.title}</h2>
                    <p>{chapter.content or ''}</p>
                </div>
                """
        
        if include_bibliography:
            html += "<h2>Bibliographie</h2>"
            references = Reference.objects.filter(project=project)
            for ref in references:
                html += f"""
                <div class="reference">
                    {ref.authors} ({ref.year}). {ref.title}. {ref.journal or 'Éditeur inconnu'}.
                </div>
                """
        
        html += "</body></html>"
        
        return Response(
            html,
            content_type='text/html',
            headers={'Content-Disposition': f'attachment; filename="{project.title}.html"'}
        )


class ChapterViewSet(viewsets.ModelViewSet):
    serializer_class = ChapterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Chapter.objects.filter(project__user=user)
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset.order_by('order')

    def perform_create(self, serializer):
        project_id = self.request.data.get('project')
        if not project_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"project": "Le champ project est requis."})
        try:
            project = Project.objects.get(id=project_id, user=self.request.user)
        except Project.DoesNotExist:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Vous n'avez pas accès à ce projet.")
        serializer.save(project=project)

    def perform_update(self, serializer):
        project = serializer.instance.project
        if project.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Vous n'avez pas accès à ce projet.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.project.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Vous n'avez pas accès à ce projet.")
        instance.delete()

    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None):
        chapter = self.get_object()
        new_order = request.data.get('order')
        if new_order is None:
            return Response(
                {'error': 'order required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        new_order = int(new_order)
        siblings = Chapter.objects.filter(
            project=chapter.project,
            parent=chapter.parent
        ).exclude(id=chapter.id)
        if new_order > chapter.order:
            siblings.filter(
                order__gt=chapter.order,
                order__lte=new_order
            ).update(order=models.F('order') - 1)
        else:
            siblings.filter(
                order__gte=new_order,
                order__lt=chapter.order
            ).update(order=models.F('order') + 1)
        chapter.order = new_order
        chapter.save()
        return Response({'status': 'reordered'})


class FolderViewSet(viewsets.ModelViewSet):
    serializer_class = FolderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Folder.objects.filter(user=self.request.user, parent=None)


class ReferenceViewSet(viewsets.ModelViewSet):
    serializer_class = ReferenceSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectOwnerOrSupervisor]

    def get_queryset(self):
        project_id = self.request.query_params.get('project_id')
        if project_id:
            return Reference.objects.filter(project_id=project_id)
        return Reference.objects.none()

    @action(detail=False, methods=['post'])
    def import_by_doi(self, request):
        doi = request.data.get('doi')
        project_id = request.data.get('project_id')
        url = f"https://api.crossref.org/works/{doi}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()['message']
            ref = Reference.objects.create(
                project_id=project_id,
                title=data.get('title', [''])[0],
                authors=', '.join([f"{a.get('family', '')} {a.get('given', '')}" for a in data.get('author', [])]),
                year=int(data.get('issued', {}).get('date-parts', [[2024]])[0][0]),
                doi=doi,
                journal=data.get('container-title', [''])[0]
            )
            return Response(ReferenceSerializer(ref).data)
        return Response({'error': 'DOI not found'}, status=404)