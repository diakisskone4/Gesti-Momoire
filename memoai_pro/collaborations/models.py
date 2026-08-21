from django.db import models
from django.contrib.auth import get_user_model
from projects.models import Project, Chapter

User = get_user_model()


class Comment(models.Model):
    """Modèle pour les commentaires sur les projets et chapitres"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name='comments')
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, null=True, blank=True, related_name='comments')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    
    content = models.TextField()
    resolved = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Commentaire de {self.user.email} - {self.created_at.strftime('%d/%m/%Y')}"


class Validation(models.Model):
    """Modèle pour la validation des chapitres par les encadreurs"""
    
    STATUS_CHOICES = [
        ('PENDING', 'En attente'),
        ('APPROVED', 'Approuvé'),
        ('REJECTED', 'Rejeté'),
        ('NEEDS_REVISION', 'Révision nécessaire'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='validations')
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, null=True, blank=True, related_name='validations')
    validator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='validations_given')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    comment = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['chapter', 'validator']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Validation de {self.chapter.title if self.chapter else self.project.title} - {self.status}"


class Collaborator(models.Model):
    """Modèle pour les collaborateurs d'un projet"""
    
    ROLE_CHOICES = [
        ('viewer', 'Lecteur'),
        ('editor', 'Éditeur'),
        ('owner', 'Propriétaire'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('active', 'Actif'),
        ('revoked', 'Révoqué'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='collaborators')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collaborations')
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    can_edit = models.BooleanField(default=False)
    can_comment = models.BooleanField(default=True)
    can_export = models.BooleanField(default=True)
    can_share = models.BooleanField(default=False)
    
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['project', 'user']
    
    def __str__(self):
        return f"{self.user.email} - {self.project.title} ({self.role})"


class ShareLink(models.Model):
    """Modèle pour les liens de partage"""
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='share_links')
    
    token = models.CharField(max_length=64, unique=True)
    can_edit = models.BooleanField(default=False)
    can_comment = models.BooleanField(default=True)
    can_export = models.BooleanField(default=True)
    
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Lien de partage - {self.project.title}"