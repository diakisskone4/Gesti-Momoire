# ai/urls.py
from django.urls import path
from .views import (
    AIChatView, AIGeneratePlanView, AIVerificationView,
    AIReformulationView, AISummaryView, AITranslationView,
    AIGenerateDiagramView, AIGenerateChartView,
    AITaskStatusView
)

urlpatterns = [
    path('chat/', AIChatView.as_view(), name='ai_chat'),
    path('generate-plan/', AIGeneratePlanView.as_view(), name='ai_generate_plan'),
    path('verify/', AIVerificationView.as_view(), name='ai_verify'),
    path('reformulate/', AIReformulationView.as_view(), name='ai_reformulate'),
    path('summarize/', AISummaryView.as_view(), name='ai_summarize'),
    path('translate/', AITranslationView.as_view(), name='ai_translate'),
    path('diagram/', AIGenerateDiagramView.as_view(), name='ai_diagram'),
    path('chart/', AIGenerateChartView.as_view(), name='ai_chart'),
    path('task/<str:task_id>/', AITaskStatusView.as_view(), name='ai_task_status'),
]