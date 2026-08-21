from django.db import models
from users.models import User

class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications_sent')
    verb = models.CharField(max_length=100)  # "commenté", "validé", "a rejoint"
    target_type = models.CharField(max_length=50)  # "project", "chapter"
    target_id = models.PositiveIntegerField()
    description = models.TextField(blank=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']