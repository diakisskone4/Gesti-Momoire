# ai/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from celery.result import AsyncResult
from .tasks import generate_plan_task, generate_diagram_task, generate_chart_task
from .services import AIService
from projects.models import Project

class AIChatView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        message = request.data.get('message')
        project_id = request.data.get('project_id')
        if not message:
            return Response({'error': 'Message required'}, status=400)
        try:
            response = AIService.chat(message, project_id, request.user)
        except Exception as e:
            return Response({'error': f'AI service error: {str(e)}'}, status=502)
        return Response({'response': response})

class AIGeneratePlanView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        project_id = request.data.get('project_id')
        try:
            project = Project.objects.get(id=project_id, user=request.user)
        except Project.DoesNotExist:
            return Response({'error': 'Project not found'}, status=404)
        if project.status != 'DRAFT':
            return Response({'error': 'Plan already generated'}, status=400)
        task = generate_plan_task.delay(project.id, project.theme)
        from .models import AIGenerationTask
        ai_task = AIGenerationTask.objects.create(
            project=project, type='plan', status='PENDING', celery_task_id=task.id
        )
        return Response({'task_id': task.id, 'ai_task_id': ai_task.id})

class AIVerificationView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        content = request.data.get('content')
        if not content:
            return Response({'error': 'Content required'}, status=400)
        result = AIService.verify(content)
        return Response(result)

class AIReformulationView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        text = request.data.get('text')
        style = request.data.get('style', 'academic')
        if not text:
            return Response({'error': 'Text required'}, status=400)
        result = AIService.reformulate(text, style)
        return Response({'result': result})

class AISummaryView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        text = request.data.get('text')
        if not text:
            return Response({'error': 'Text required'}, status=400)
        result = AIService.summarize(text)
        return Response({'summary': result})

class AITranslationView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        text = request.data.get('text')
        target_lang = request.data.get('target_lang', 'en')
        if not text:
            return Response({'error': 'Text required'}, status=400)
        result = AIService.translate(text, target_lang)
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
    permission_classes = [IsAuthenticated]
    def get(self, request, task_id):
        result = AsyncResult(task_id)
        if result.ready():
            return Response({'status': 'completed', 'result': result.result})
        return Response({'status': 'pending'})