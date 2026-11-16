from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email requis')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('STUDENT', 'Étudiant'),
        ('SUPERVISOR', 'Encadreur'),
        ('CO_SUPERVISOR', 'Co-encadreur'),
        ('JURY', 'Membre du jury'),
        ('ADMIN', 'Administrateur'),
    )
    LEVEL_CHOICES = (
        ('LICENCE', 'Licence'),
        ('MASTER', 'Master'),
        ('DOCTORAT', 'Doctorat'),
    )
    SUPERVISOR_ROLES = ('SUPERVISOR', 'CO_SUPERVISOR')
    REVIEWER_ROLES = ('SUPERVISOR', 'CO_SUPERVISOR', 'JURY')
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, blank=True)
    photo = models.URLField(blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='STUDENT')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    language = models.CharField(max_length=10, default='fr')

    # Rattachement académique (tous rôles sauf administrateur)
    university = models.CharField(max_length=200, blank=True)
    faculty = models.CharField(max_length=200, blank=True)
    department = models.CharField(max_length=200, blank=True)
    # Étudiant
    student_number = models.CharField(max_length=50, blank=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, blank=True)
    # Encadreur / co-encadreur / jury
    academic_title = models.CharField(max_length=100, blank=True)
    speciality = models.CharField(max_length=200, blank=True)

    # Sécurité du compte
    email_verified = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    totp_code = models.CharField(max_length=6, blank=True)

    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set',
        related_query_name='user',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_permissions_set',
        related_query_name='user',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.email

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    university = models.CharField(max_length=200, blank=True)
    faculty = models.CharField(max_length=200, blank=True)
    department = models.CharField(max_length=200, blank=True)
    # autres champs...

class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)