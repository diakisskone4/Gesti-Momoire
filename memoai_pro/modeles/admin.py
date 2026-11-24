from django.contrib import admin

from .models import MemoirTemplate, PaymentDevice, PaymentMessage, TemplatePurchase


@admin.register(MemoirTemplate)
class MemoirTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'level', 'cover_style', 'price', 'currency', 'is_active', 'order']
    list_editable = ['price', 'is_active', 'order']
    prepopulated_fields = {'slug': ['name']}


@admin.register(TemplatePurchase)
class TemplatePurchaseAdmin(admin.ModelAdmin):
    list_display = ['user', 'template', 'status', 'amount', 'amount_charged', 'created_at', 'paid_at']
    list_filter = ['status', 'provider', 'operator', 'template']
    search_fields = ['user__email', 'transaction_reference', 'checkout_session_id']
    readonly_fields = ['checkout_session_id', 'checkout_url', 'transaction_id', 'transaction_reference',
                       'amount_charged', 'operator', 'payer_phone', 'submitted_at', 'reviewed_by', 'created_at',
                       'paid_at']


@admin.register(PaymentDevice)
class PaymentDeviceAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'last_seen_at', 'created_at']
    readonly_fields = ['token_hash', 'last_seen_at', 'created_at']


@admin.register(PaymentMessage)
class PaymentMessageAdmin(admin.ModelAdmin):
    list_display = ['operator', 'amount', 'received_at', 'purchase']
    list_filter = ['operator']
    readonly_fields = [f.name for f in PaymentMessage._meta.fields]
