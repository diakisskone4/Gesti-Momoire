from rest_framework import serializers
from users.serializers import UserPublicSerializer
from .models import Project, Chapter, Reference, Folder

class FolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = ['id', 'name', 'parent', 'created_at']


class ChapterSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = ['id', 'project', 'parent', 'order', 'title', 'content', 'type', 'status', 'version', 'created_at', 'updated_at', 'children']
        read_only_fields = ['project']  # Le project ne peut pas être modifié via PUT/PATCH

    def get_children(self, obj):
        return ChapterSerializer(obj.children.all(), many=True).data


class ProjectSerializer(serializers.ModelSerializer):
    chapters = ChapterSerializer(many=True, read_only=True)
    owner = UserPublicSerializer(source='user', read_only=True)
    supervisor_detail = UserPublicSerializer(source='supervisor', read_only=True)
    co_supervisor_detail = UserPublicSerializer(source='co_supervisor', read_only=True)
    jury_detail = UserPublicSerializer(source='jury', many=True, read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    my_role = serializers.SerializerMethodField()
    template_detail = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = [
            'user', 'created_at', 'updated_at', 'export_allowed', 'status',
            'archived_at', 'status_before_archive', 'submitted_at', 'validated_at', 'review_comment',
            'template',  # attribué uniquement via /modeles/<slug>/apply/ (modèle payant)
        ]

    def get_template_detail(self, obj):
        t = obj.template
        if not t:
            return None
        return {'slug': t.slug, 'name': t.name, 'cover_style': t.cover_style, 'paid': t.is_owned_by(obj.user)}

    def get_my_role(self, obj):
        """Rôle de l'utilisateur courant sur CE mémoire."""
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return None
        if obj.user_id == user.id:
            return 'OWNER'
        if obj.supervisor_id == user.id:
            return 'SUPERVISOR'
        if obj.co_supervisor_id == user.id:
            return 'CO_SUPERVISOR'
        if obj.jury.filter(pk=user.pk).exists():
            return 'JURY'
        return 'ADMIN' if user.role == 'ADMIN' else None

    def validate_supervisor(self, value):
        if value and value.role != 'SUPERVISOR':
            raise serializers.ValidationError("Cet utilisateur n'est pas un encadreur.")
        return value

    def validate_co_supervisor(self, value):
        if value and value.role not in ('SUPERVISOR', 'CO_SUPERVISOR'):
            raise serializers.ValidationError("Cet utilisateur n'est pas un co-encadreur.")
        return value

    def validate_jury(self, value):
        if any(member.role != 'JURY' for member in value):
            raise serializers.ValidationError('Tous les membres doivent avoir le rôle Jury.')
        return value

    def validate(self, attrs):
        supervisor = attrs.get('supervisor', getattr(self.instance, 'supervisor', None))
        co_supervisor = attrs.get('co_supervisor', getattr(self.instance, 'co_supervisor', None))
        if supervisor and co_supervisor and supervisor == co_supervisor:
            raise serializers.ValidationError({'co_supervisor': "Le co-encadreur doit être différent de l'encadreur."})
        return attrs


class ReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reference
        fields = '__all__'