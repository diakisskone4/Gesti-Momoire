from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="MemoAI API",
        default_version='v1',
        description="API pour l'application MemoAI - Gestion de mémoires",
    ),
    public=settings.DEBUG,
    permission_classes=[permissions.AllowAny if settings.DEBUG else permissions.IsAdminUser],
)

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),

    # APIs
    path('projects/', include('projects.urls')),
    path('projects/', include('collaborations.urls')),
    path('users/', include('users.urls')),
    path('ai/', include('ai.urls')),
    path('notifications/', include('notifications.urls')),
    path('documents/', include('documents.urls')),
    path('payments/', include('payments.urls')),
    path('dashboard/', include('admin_dashboard.urls')),
    path('modeles/', include('modeles.urls')),
]

# Documentation de l'API : désactivée en production (elle donnerait la carte complète de l'API).
if settings.ENABLE_API_DOCS:
    urlpatterns += [
        path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
        path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
        path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
