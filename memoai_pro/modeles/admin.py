from django.contrib import admin

from .models import MemoirTemplate, TemplatePurchase


@admin.register(MemoirTemplate)
class MemoirTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'level', 'cover_style', 'price', 'currency', 'is_active', 'order']
    list_editable = ['price', 'is_active', 'order']
    prepopulated_fields = {'slug': ['name']}


@admin.register(TemplatePurchase)
class TemplatePurchaseAdmin(admin.ModelAdmin):
    list_display = ['user', 'template', 'status', 'amount', 'amount_charged', 'created_at', 'paid_at']
    list_filter = ['status', 'template']
    search_fields = ['user__email', 'transaction_reference', 'checkout_session_id']
    readonly_fields = ['checkout_session_id', 'checkout_url', 'transaction_id', 'transaction_reference',
                       'amount_charged', 'created_at', 'paid_at']
