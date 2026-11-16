import json
import logging

from celery import shared_task
from kombu.exceptions import OperationalError

from .models import AIGenerationTask
from .services import AIError, AIService
from projects.models import Project

logger = logging.getLogger(__name__)


def start_plan_generation(project):
    """Crée le suivi de génération puis lance la tâche (§6.3).
    Lève OperationalError si le broker Celery (Redis) est injoignable."""
    ai_task = AIGenerationTask.objects.create(project=project, type='plan', status='PENDING')
    try:
        result = generate_plan_task.delay(ai_task.id)
    except OperationalError:
        ai_task.status = 'FAILED'
        ai_task.error_message = 'File de tâches indisponible (Redis).'
        ai_task.save(update_fields=['status', 'error_message', 'updated_at'])
        raise
    ai_task.celery_task_id = result.id or ''
    ai_task.save(update_fields=['celery_task_id', 'updated_at'])
    ai_task.refresh_from_db()
    return ai_task


@shared_task
def generate_plan_task(ai_task_id):
    task_record = AIGenerationTask.objects.select_related('project').get(id=ai_task_id)
    project = task_record.project
    task_record.status = 'PROCESSING'
    task_record.save(update_fields=['status', 'updated_at'])
    try:
        from .generation import project_context, rebuild_plan, template_guide
        plan_data = json.loads(AIService.generate_plan(
            project.theme or project.title,
            context=project_context(project),
            guide=template_guide(project.template) if project.template_id else '',
        ))
        if not plan_data.get('chapters'):
            raise AIError("L'IA a renvoyé un plan vide. Réessayez.", 502)
        rebuild_plan(project, plan_data)

        task_record.result = plan_data
        task_record.status = 'COMPLETED'
        task_record.save(update_fields=['result', 'status', 'updated_at'])
    except AIError as e:
        task_record.status = 'FAILED'
        task_record.error_message = str(e)
        task_record.save(update_fields=['status', 'error_message', 'updated_at'])
    except Exception:
        logger.exception('Échec de la génération du plan (tâche %s)', ai_task_id)
        task_record.status = 'FAILED'
        task_record.error_message = "La génération du plan a échoué. Vérifiez la configuration de l'IA et réessayez."
        task_record.save(update_fields=['status', 'error_message', 'updated_at'])


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
