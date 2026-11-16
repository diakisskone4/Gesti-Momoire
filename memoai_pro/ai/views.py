# ai/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from kombu.exceptions import OperationalError
from .tasks import start_plan_generation, generate_diagram_task, generate_chart_task
from .services import AIService
from projects.models import Project
import logging
from .services import AIError

logger = logging.getLogger(__name__)


def call_ai(fn, *args):
    """Appelle l'IA ; les erreurs (déjà traduites en AIError par le service)
    deviennent une réponse lisible, les détails restent dans les logs."""
    try:
        return fn(*args), None
    except AIError as e:
        headers = {'Retry-After': str(int(e.retry_after))} if e.retry_after else None
        return None, Response({'error': str(e), 'retry_after': e.retry_after}, status=e.status, headers=headers)

class AIChatView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        message = request.data.get('message')
        project_id = request.data.get('project_id')
        if not message:
            return Response({'error': 'Message required'}, status=400)
        response, error = call_ai(AIService.chat, message, project_id, request.user)
        if error:
            return error
        return Response({'response': response})

class AIGeneratePlanView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        project_id = request.data.get('project_id')
        try:
            project = Project.objects.get(id=project_id, user=request.user)
        except (Project.DoesNotExist, ValueError, TypeError):
            return Response({'error': 'Mémoire introuvable.'}, status=404)
        return plan_generation_response(project)


def plan_generation_response(project):
    """Lance la génération du plan et renvoie son suivi (statut, erreur, résultat).
    Réservé aux mémoires avec un modèle acheté et sans texte déjà rédigé."""
    from .generation import check_plan_allowed
    check_plan_allowed(project)
    try:
        ai_task = start_plan_generation(project)
    except OperationalError:
        logger.error('Celery broker unreachable: plan generation not queued')
        return Response({'error': 'Le service de génération est indisponible (file de tâches Redis arrêtée). Réessayez plus tard.'}, status=503)
    return Response(ai_task_payload(ai_task), status=200 if ai_task.status in ('COMPLETED', 'FAILED') else 202)


def ai_task_payload(ai_task):
    return {
        'ai_task_id': ai_task.id,
        'status': ai_task.status,
        'error': ai_task.error_message or None,
        'result': ai_task.result,
    }


class AIVerificationView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        content = request.data.get('content')
        if not content:
            return Response({'error': 'Content required'}, status=400)
        result, error = call_ai(AIService.verify, content)
        if error:
            return error
        return Response(result)

class AIReformulationView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        text = request.data.get('text')
        style = request.data.get('style', 'academic')
        if not text:
            return Response({'error': 'Text required'}, status=400)
        result, error = call_ai(AIService.reformulate, text, style)
        if error:
            return error
        return Response({'result': result})

class AISummaryView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        text = request.data.get('text')
        if not text:
            return Response({'error': 'Text required'}, status=400)
        result, error = call_ai(AIService.summarize, text)
        if error:
            return error
        return Response({'summary': result})

class AITranslationView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        text = request.data.get('text')
        target_lang = request.data.get('target_lang', 'en')
        if not text:
            return Response({'error': 'Text required'}, status=400)
        result, error = call_ai(AIService.translate, text, target_lang)
        if error:
            return error
        return Response({'translation': result})

class AIGenerateDiagramView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        diagram_type = request.data.get('type', 'uml')  # uml, bpmn, flowchart
        description = request.data.get('description')
        if not description:
            return Response({'error': 'Description required'}, status=400)
        task = generate_diagram_task.delay(diagram_type, description)
        return Response({'task_id': task.id})

class AIGenerateChartView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        chart_type = request.data.get('type', 'bar')
        data = request.data.get('data')
        if not data:
            return Response({'error': 'Data required'}, status=400)
        task = generate_chart_task.delay(chart_type, data)
        return Response({'task_id': task.id})

class AITaskStatusView(APIView):
    """Suivi d'une génération IA à partir de l'enregistrement en base (pas de dépendance à Redis)."""
    permission_classes = [IsAuthenticated]
    def get(self, request, task_id):
        from .models import AIGenerationTask
        ai_task = AIGenerationTask.objects.filter(id=task_id, project__user=request.user).first()
        if not ai_task:
            return Response({'error': 'Tâche introuvable.'}, status=404)
        return Response(ai_task_payload(ai_task))
