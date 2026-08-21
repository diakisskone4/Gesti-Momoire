from django.contrib import admin
from .models import Comment, Validation, Collaborator, ShareLink

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'content', 'resolved', 'created_at']
    list_filter = ['resolved', 'created_at']
    search_fields = ['user__email', 'content']

@admin.register(Validation)
class ValidationAdmin(admin.ModelAdmin):
    list_display = ['project', 'chapter', 'validator', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['project__title', 'validator__email']

@admin.register(Collaborator)
class CollaboratorAdmin(admin.ModelAdmin):
    list_display = ['project', 'user', 'role', 'status']
    list_filter = ['role', 'status']
    search_fields = ['project__title', 'user__email']

@admin.register(ShareLink)
class ShareLinkAdmin(admin.ModelAdmin):
    list_display = ['project', 'token', 'created_at']
    search_fields = ['project__title', 'token']