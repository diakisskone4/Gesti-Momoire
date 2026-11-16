from rest_framework import serializers
from .models import Comment, Validation, Collaborator, ShareLink
from users.serializers import UserBasicSerializer


class CommentSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = ['id', 'user', 'project', 'chapter', 'parent', 'content', 'resolved', 'replies', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']
    
    def get_replies(self, obj):
        return CommentSerializer(obj.replies.all(), many=True).data


class ValidationSerializer(serializers.ModelSerializer):
    validator = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = Validation
        fields = ['id', 'project', 'chapter', 'validator', 'status', 'comment', 'created_at', 'updated_at']
        read_only_fields = ['validator', 'created_at', 'updated_at']
        # validator est fixé par la vue : l'unicité (chapitre, validateur) est vérifiée dans perform_create.
        validators = []


class CollaboratorSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Collaborator
        fields = ['id', 'project', 'user', 'user_email', 'user_name', 'role', 'status', 
                  'can_edit', 'can_comment', 'can_export', 'can_share', 'invited_at', 'accepted_at']
        read_only_fields = ['user', 'invited_at', 'accepted_at']
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email


class ShareLinkSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    
    class Meta:
        model = ShareLink
        fields = ['token', 'project', 'can_edit', 'can_comment', 'can_export', 'expires_at', 'created_at', 'url']
        read_only_fields = ['token', 'created_at']
    
    def get_url(self, obj):
        return f"/share/{obj.token}"