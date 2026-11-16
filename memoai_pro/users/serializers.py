# users/serializers.py
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.utils.crypto import constant_time_compare
from rest_framework import serializers

from .models import User

# Champs obligatoires à l'inscription selon le rôle (cahier des charges §2)
ROLE_REQUIRED_FIELDS = {
    'STUDENT': ['university', 'level'],
    'SUPERVISOR': ['university', 'academic_title'],
    'CO_SUPERVISOR': ['university', 'academic_title'],
    'JURY': ['academic_title'],
    'ADMIN': [],
}

PUBLIC_USER_FIELDS = [
    'id', 'email', 'first_name', 'last_name', 'full_name', 'role', 'photo',
    'university', 'faculty', 'department', 'academic_title', 'speciality',
]


class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'role', 'photo']


class UserPublicSerializer(serializers.ModelSerializer):
    """Profil visible par les autres utilisateurs (choix d'un encadreur, jury...)."""
    class Meta:
        model = User
        fields = PUBLIC_USER_FIELDS


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    admin_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'phone', 'password', 'password2',
            'role', 'language', 'university', 'faculty', 'department',
            'student_number', 'level', 'academic_title', 'speciality', 'admin_code',
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': 'Les mots de passe ne correspondent pas.'})

        role = attrs.get('role', 'STUDENT')
        missing = {
            field: 'Ce champ est obligatoire pour ce profil.'
            for field in ROLE_REQUIRED_FIELDS.get(role, [])
            if not attrs.get(field)
        }
        if missing:
            raise serializers.ValidationError(missing)

        if role == 'ADMIN':
            # Un compte administrateur ne peut être créé qu'avec le code secret
            # défini côté serveur (ADMIN_REGISTRATION_CODE).
            expected = getattr(settings, 'ADMIN_REGISTRATION_CODE', '')
            given = attrs.get('admin_code', '')
            if not expected or not constant_time_compare(given, expected):
                raise serializers.ValidationError({'admin_code': "Code d'accès administrateur invalide."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        validated_data.pop('admin_code', None)
        if validated_data.get('role') == 'ADMIN':
            validated_data['is_staff'] = True
        return User.objects.create_user(**validated_data)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'phone', 'photo',
            'role', 'language', 'university', 'faculty', 'department',
            'student_number', 'level', 'academic_title', 'speciality',
            'email_verified', 'two_factor_enabled', 'created_at',
        ]
        read_only_fields = ['id', 'email', 'role', 'email_verified', 'two_factor_enabled', 'created_at']


class AdminUserSerializer(serializers.ModelSerializer):
    """Gestion des utilisateurs par l'administrateur (§3.17)."""
    projects_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'phone', 'role',
            'is_active', 'university', 'faculty', 'department', 'level',
            'academic_title', 'speciality', 'projects_count', 'created_at',
        ]
        read_only_fields = ['id', 'email', 'created_at']

    def update(self, instance, validated_data):
        role = validated_data.get('role', instance.role)
        validated_data['is_staff'] = role == 'ADMIN' or instance.is_superuser
        return super().update(instance, validated_data)
