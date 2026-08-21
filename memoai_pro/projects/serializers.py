from rest_framework import serializers
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
    
    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at', 'export_allowed']


class ReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reference
        fields = '__all__'