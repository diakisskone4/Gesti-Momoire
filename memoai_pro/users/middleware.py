# users/middleware.py
import logging
from django.utils.timezone import now

logger = logging.getLogger(__name__)

class ActivityLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            # Log l'activité (on peut stocker dans un modèle ActivityLog)
            logger.info(f"{now()} - {user.email} - {request.method} {request.path}")
        return response