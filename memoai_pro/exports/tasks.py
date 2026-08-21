from celery import shared_task
from projects.models import Project
from .services import ExportService

@shared_task
def export_project_task(project_id, format):
    project = Project.objects.get(id=project_id)
    # Générer le document
    file_path = ExportService.export(project, format)
    # Stocker sur S3 et retourner l'URL
    # (implémentation simplifiée)
    return {'url': f'https://storage.example.com/{file_path}'}