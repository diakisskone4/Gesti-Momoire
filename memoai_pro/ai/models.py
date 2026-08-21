from django.db import models
from projects.models import Project

class AIGenerationTask(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='ai_tasks')
    type = models.CharField(max_length=50)  # plan, reformulation, verification, etc.
    status = models.CharField(max_length=20, choices=(
        ('PENDING', 'En attente'),
        ('PROCESSING', 'En cours'),
        ('COMPLETED', 'Terminé'),
        ('FAILED', 'Échoué'),
    ), default='PENDING')
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    celery_task_id = models.CharField(max_length=255, blank=True)