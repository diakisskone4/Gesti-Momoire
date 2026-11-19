from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ActiveManager(models.Manager):
    """Gestionnaire par défaut : masque les éléments placés dans la corbeille."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Project(models.Model):
    LEVEL_CHOICES = [
        ('LICENCE', 'Licence'),
        ('MASTER', 'Master'),
        ('DOCTORAT', 'Doctorat'),
    ]
    
    # Cycle de vie du mémoire (cahier des charges §6.6)
    STATUS_CHOICES = [
        ('DRAFT', 'Brouillon'),
        ('IN_PROGRESS', 'En cours de rédaction'),
        ('REVIEW', 'En relecture'),
        ('VALIDATED', 'Validé'),
        ('ARCHIVED', 'Archivé'),
        ('COMPLETED', 'Terminé'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    folder = models.ForeignKey('Folder', on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')

    # Encadrement et jury (§2, §3.4)
    supervisor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='supervised_projects', limit_choices_to={'role': 'SUPERVISOR'},
    )
    co_supervisor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='co_supervised_projects', limit_choices_to={'role__in': ['SUPERVISOR', 'CO_SUPERVISOR']},
    )
    # Modèle de mémoire acheté appliqué à ce mémoire (page de garde + plan)
    template = models.ForeignKey(
        'modeles.MemoirTemplate', on_delete=models.SET_NULL, null=True, blank=True, related_name='projects',
    )
    jury = models.ManyToManyField(
        User, blank=True, related_name='jury_projects', limit_choices_to={'role': 'JURY'},
    )
    
    title = models.CharField(max_length=255)
    theme = models.CharField(max_length=255, blank=True, null=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='MASTER')
    
    university = models.CharField(max_length=255, blank=True, null=True)
    faculty = models.CharField(max_length=255, blank=True, null=True)
    department = models.CharField(max_length=255, blank=True, null=True)
    field_of_study = models.CharField(max_length=255, blank=True, null=True)
    
    option = models.CharField(max_length=255, blank=True, null=True)
    laboratory = models.CharField(max_length=255, blank=True, null=True)
    
    country = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    
    academic_year = models.CharField(max_length=20, blank=True, null=True)
    language = models.CharField(max_length=10, default='fr')
    desired_pages = models.IntegerField(default=40)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    is_favorite = models.BooleanField(default=False)
    tags = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    status_before_archive = models.CharField(max_length=20, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    review_comment = models.TextField(blank=True)
    
    export_allowed = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)  # dans la corbeille

    objects = ActiveManager()
    all_objects = models.Manager()  # y compris la corbeille

    def __str__(self):
        return self.title


class Chapter(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('review', 'En révision'),
        ('validated', 'Validé'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='chapters')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    order = models.IntegerField(default=0)
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=50, default='chapter')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    version = models.IntegerField(default=1)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)  # dans la corbeille

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['order']
        base_manager_name = 'all_objects'
    
    def __str__(self):
        return f"{self.title} (Projet: {self.project.title})"


class Folder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='folders')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Reference(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='references')
    
    title = models.CharField(max_length=500)
    authors = models.CharField(max_length=500)
    year = models.IntegerField()
    journal = models.CharField(max_length=255, blank=True, null=True)
    doi = models.CharField(max_length=255, blank=True, null=True)
    isbn = models.CharField(max_length=20, blank=True, null=True)
    bibtex = models.TextField(blank=True, null=True)
    style = models.CharField(max_length=50, default='apa')
    
    # ✅ CORRECTION: Utiliser uniquement auto_now_add=True, pas de default
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)  # dans la corbeille

    objects = ActiveManager()
    all_objects = models.Manager()

    def __str__(self):
        return self.title

class ProjectImage(models.Model):
    """Image (figure, photo, schéma, graphique) insérée dans un mémoire.

    Stockée dans la base de données : l'hébergement (Vercel) n'a pas de disque permanent.
    Les images sont redimensionnées à l'envoi (1600 px maximum) pour rester légères.
    Dans le texte d'un chapitre, une figure s'écrit sur sa propre ligne : [Figure:ID | légende].
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='images')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    data = models.BinaryField()
    content_type = models.CharField(max_length=30)
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'Image {self.id} ({self.width}×{self.height}) — {self.project_id}'
