from django.http import JsonResponse
from .models import DashboardMessage


def active_messages(request):
    messages = DashboardMessage.objects.filter(is_active=True).order_by('-updated_at')
    payload = [
        {
            'id': message.id,
            'title': message.title,
            'content': message.content,
            'created_at': message.created_at.isoformat(),
            'updated_at': message.updated_at.isoformat(),
        }
        for message in messages
    ]
    return JsonResponse({'messages': payload})
