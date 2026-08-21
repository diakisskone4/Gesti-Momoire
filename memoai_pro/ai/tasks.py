from celery import shared_task
from .models import AIGenerationTask
from .services import AIService
from projects.models import Project, Chapter
import json

@shared_task
def generate_plan_task(project_id, theme):
    task_record = None
    try:
        task_record = AIGenerationTask.objects.get(project_id=project_id, type='plan')
        task_record.status = 'PROCESSING'
        task_record.save()

        plan_json = AIService.generate_plan(theme)
        plan_data = json.loads(plan_json)

        project = Project.objects.get(id=project_id)
        # Créer les chapitres à partir du plan
        for chapter_data in plan_data.get('chapters', []):
            Chapter.objects.create(
                project=project,
                title=chapter_data.get('title', 'Chapitre'),
                order=chapter_data.get('order', 0),
                type='chapter'
            )
            # pour les sous-sections, on pourrait les ajouter en tant qu'enfants
        
        # Stocker le plan complet en résultat
        task_record.result = plan_data
        task_record.status = 'COMPLETED'
        task_record.save()

        # Mettre à jour le statut du projet
        project.status = 'PLAN_GENERATED'
        project.save()
    except Exception as e:
        if task_record is not None:
            task_record.status = 'FAILED'
            task_record.error_message = str(e)
            task_record.save()


@shared_task
def generate_diagram_task(diagram_type, description):
    return {
        'diagram_type': diagram_type,
        'description': description,
        'status': 'queued'
    }


@shared_task
def generate_chart_task(chart_type, data):
    return {
        'chart_type': chart_type,
        'data': data,
        'status': 'queued'
    }
