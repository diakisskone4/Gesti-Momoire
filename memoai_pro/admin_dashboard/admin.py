from django.contrib import admin
from .models import DashboardMessage


@admin.register(DashboardMessage)
class DashboardMessageAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'content')
    ordering = ('-updated_at',)
