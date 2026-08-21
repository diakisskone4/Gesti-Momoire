from django.urls import path
from .views import active_messages

urlpatterns = [
    path('active-messages/', active_messages, name='admin_dashboard_active_messages'),
]
