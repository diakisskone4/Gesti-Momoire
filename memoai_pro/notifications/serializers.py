from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'actor', 'actor_name', 'verb', 'target_type', 'target_id', 'description', 'read', 'created_at']
        read_only_fields = fields

    def get_actor_name(self, obj):
        return obj.actor.full_name if obj.actor else None
