"""Règles d'accès aux mémoires, partagées par toutes les applications.

- Lecture : l'auteur, l'encadreur, le co-encadreur, les membres du jury, l'administrateur.
- Écriture (chapitres, références, collaborateurs...) : l'auteur seul.
"""
from django.db.models import Q
from rest_framework.exceptions import NotFound, PermissionDenied

from .models import Project


def visible_projects(user):
    if user.role == 'ADMIN':
        return Project.objects.all()
    return Project.objects.filter(
        Q(user=user) | Q(supervisor=user) | Q(co_supervisor=user) | Q(jury=user)
    ).distinct()


def readable_project_q(user, prefix='project__'):
    """Filtre Q sur un modèle lié à Project (chapitres, références, commentaires...)."""
    active = Q(**{f'{prefix}deleted_at__isnull': True})  # mémoire hors corbeille
    if user.role == 'ADMIN':
        return active
    return active & (
        Q(**{f'{prefix}user': user}) | Q(**{f'{prefix}supervisor': user})
        | Q(**{f'{prefix}co_supervisor': user}) | Q(**{f'{prefix}jury': user})
    )


def is_reviewer(project, user):
    return user.id in (project.supervisor_id, project.co_supervisor_id) or project.jury.filter(pk=user.pk).exists()


def can_read(project, user):
    return user.role == 'ADMIN' or project.user_id == user.id or is_reviewer(project, user)


def get_readable_project(user, project_id):
    if not project_id:
        raise NotFound('Mémoire introuvable.')
    project = visible_projects(user).filter(pk=project_id).first() if str(project_id).isdigit() else None
    if project is None:
        raise NotFound('Mémoire introuvable.')
    return project


def get_owned_project(user, project_id):
    project = get_readable_project(user, project_id)
    if project.user_id != user.id:
        raise PermissionDenied("Seul l'auteur du mémoire peut effectuer cette action.")
    return project
