"""Point d'entrée ASGI : HTTP (Django) + WebSockets (Channels, authentifiés par JWT)."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
# Django doit être initialisé avant d'importer les consumers (modèles).
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from django.urls import path  # noqa: E402

from collaborations.consumers import DocumentConsumer  # noqa: E402
from notifications.consumers import NotificationConsumer  # noqa: E402
from users.ws_auth import JWTAuthMiddleware  # noqa: E402

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': JWTAuthMiddleware(
        URLRouter([
            path('ws/notifications/<int:user_id>/', NotificationConsumer.as_asgi()),
            path('ws/document/<int:project_id>/', DocumentConsumer.as_asgi()),
        ])
    ),
})
