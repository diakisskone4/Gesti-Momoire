from rest_framework import serializers

from . import services
from .models import MemoirTemplate, TemplatePurchase


class MemoirTemplateSerializer(serializers.ModelSerializer):
    owned = serializers.SerializerMethodField()
    is_free = serializers.BooleanField(read_only=True)
    level_label = serializers.CharField(source='get_level_display', read_only=True)
    cover_label = serializers.CharField(source='get_cover_style_display', read_only=True)
    outline = serializers.SerializerMethodField()
    structure = serializers.SerializerMethodField()

    class Meta:
        model = MemoirTemplate
        fields = ['slug', 'name', 'tagline', 'description', 'level', 'level_label', 'domain', 'cover_style',
                  'cover_label', 'accent_color', 'price', 'currency', 'is_free', 'owned', 'outline', 'structure']

    def _owned_ids(self):
        return self.context.get('owned_ids', set())

    def get_owned(self, obj):
        return obj.is_free or obj.id in self._owned_ids()

    def get_outline(self, obj):
        """Aperçu public du plan : titres seulement."""
        return [{'title': e['title'], 'type': e.get('type', 'chapter'),
                 'sections': [s['title'] for s in e.get('sections', [])]} for e in obj.structure]

    def get_structure(self, obj):
        """Plan complet avec conseils : réservé aux acheteurs."""
        return obj.structure if self.get_owned(obj) else None


class TemplatePurchaseSerializer(serializers.ModelSerializer):
    template_slug = serializers.CharField(source='template.slug', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    checkout_url = serializers.SerializerMethodField()

    def get_checkout_url(self, obj):
        """Lien de paiement encore utilisable, sinon vide (lien expiré, ancien prestataire ou autre mode)."""
        return obj.checkout_url if services.is_payable(obj) else ''

    class Meta:
        model = TemplatePurchase
        fields = ['id', 'template_slug', 'template_name', 'status', 'amount', 'currency', 'amount_charged',
                  'checkout_url', 'transaction_reference', 'created_at', 'paid_at']
        read_only_fields = fields
