"""Corbeille : les mémoires, chapitres et références supprimés y restent 30 jours.

DELETE sur un mémoire, un chapitre ou une référence les place dans la corbeille (voir `move_to_trash`).

GET  /projects/trash/            éléments de la corbeille de l'auteur
POST /projects/trash/restore/    {kind, id}  remet l'élément à sa place
POST /projects/trash/delete/     {kind, id}  suppression définitive
POST /projects/trash/empty/                  vide toute la corbeille

Passé RETENTION_DAYS, les éléments sont supprimés définitivement (à la consultation de la corbeille).
"""
from datetime import timedelta

from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Chapter, Project, Reference

RETENTION_DAYS = 30
KINDS = ('project', 'chapter', 'reference')


# ------------------------------------------------------------------ mise à la corbeille

def _descendants(chapter):
    """Le chapitre et toutes ses sections, quel que soit leur niveau (hors corbeille)."""
    found, frontier = [chapter], [chapter.id]
    while frontier:
        children = list(Chapter.objects.filter(parent_id__in=frontier))
        found += children
        frontier = [c.id for c in children]
    return found


def move_to_trash(instance):
    """Place un mémoire, un chapitre (avec ses sections) ou une référence dans la corbeille."""
    now = timezone.now()
    if isinstance(instance, Chapter):
        # Même date pour le chapitre et ses sections : ils seront restaurés ensemble.
        ids = [c.id for c in _descendants(instance)]
        Chapter.all_objects.filter(id__in=ids).update(deleted_at=now)
    else:
        type(instance).all_objects.filter(pk=instance.pk).update(deleted_at=now)
    instance.deleted_at = now


# ------------------------------------------------------------------ contenu de la corbeille

def _trashed(user):
    """Éléments de la corbeille de l'auteur. Les chapitres et références d'un mémoire lui-même
    dans la corbeille n'apparaissent pas séparément : ils reviennent avec le mémoire."""
    projects = Project.all_objects.filter(user=user, deleted_at__isnull=False)
    chapters = Chapter.all_objects.filter(project__user=user, project__deleted_at__isnull=True,
                                          deleted_at__isnull=False).select_related('project', 'parent')
    # Seules les racines : une section supprimée avec son chapitre est restaurée avec lui.
    chapters = [c for c in chapters if not (c.parent and c.parent.deleted_at == c.deleted_at)]
    references = Reference.all_objects.filter(project__user=user, project__deleted_at__isnull=True,
                                              deleted_at__isnull=False).select_related('project')
    return projects, chapters, references


def purge_expired(user):
    limit = timezone.now() - timedelta(days=RETENTION_DAYS)
    Project.all_objects.filter(user=user, deleted_at__lt=limit).delete()
    Chapter.all_objects.filter(project__user=user, deleted_at__lt=limit).delete()
    Reference.all_objects.filter(project__user=user, deleted_at__lt=limit).delete()


def _item(kind, obj, project, details):
    return {
        'kind': kind, 'id': obj.id, 'title': obj.title, 'details': details,
        'project_id': project.id, 'project_title': project.title,
        'deleted_at': obj.deleted_at, 'purge_at': obj.deleted_at + timedelta(days=RETENTION_DAYS),
    }


def _plural(n, word):
    return f"{n} {word}{'s' if n > 1 else ''}"


def trash_items(user):
    projects, chapters, references = _trashed(user)
    items = []
    for project in projects:
        n = Chapter.all_objects.filter(project=project, parent__isnull=True, deleted_at__isnull=True).count()
        items.append(_item('project', project, project, f"Mémoire · {_plural(n, 'chapitre')}"))
    for chapter in chapters:
        n = Chapter.all_objects.filter(project=chapter.project, deleted_at=chapter.deleted_at).count() - 1
        label = 'Section' if chapter.parent_id else 'Chapitre'
        items.append(_item('chapter', chapter, chapter.project,
                           f"{label} · {_plural(n, 'section')}" if n else label))
    for reference in references:
        items.append(_item('reference', reference, reference.project,
                           f'Référence · {reference.authors} ({reference.year})'))
    items.sort(key=lambda item: item['deleted_at'], reverse=True)
    return items


def _get(user, kind, pk):
    if kind not in KINDS:
        raise ValidationError({'error': 'Type d’élément inconnu.'})
    try:
        pk = int(pk)
    except (TypeError, ValueError):
        raise ValidationError({'error': 'Identifiant invalide.'})
    projects, chapters, references = _trashed(user)
    pool = {'project': projects, 'chapter': chapters, 'reference': references}[kind]
    found = next((obj for obj in pool if obj.id == pk), None)
    if found is None:
        raise NotFound('Cet élément n’est plus dans la corbeille.')
    return found


def restore(obj):
    with transaction.atomic():
        if isinstance(obj, Chapter):
            batch = Chapter.all_objects.filter(project=obj.project, deleted_at=obj.deleted_at)
            if obj.parent_id and obj.parent.deleted_at is not None:
                # Le chapitre parent est lui aussi dans la corbeille : la section revient en fin de plan.
                last = Chapter.objects.filter(project=obj.project, parent=None).aggregate(m=Max('order'))['m'] or 0
                Chapter.all_objects.filter(pk=obj.pk).update(parent=None, order=last + 1)
            batch.update(deleted_at=None)
        else:
            type(obj).all_objects.filter(pk=obj.pk).update(deleted_at=None)


def delete_forever(obj):
    if isinstance(obj, Chapter):
        Chapter.all_objects.filter(project=obj.project, deleted_at=obj.deleted_at).delete()
    else:
        obj.delete()


# ------------------------------------------------------------------ API

class TrashView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        purge_expired(request.user)
        return Response({'retention_days': RETENTION_DAYS, 'items': trash_items(request.user)})


class TrashRestoreView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        obj = _get(request.user, request.data.get('kind'), request.data.get('id'))
        restore(obj)
        return Response({'status': 'restored', 'title': obj.title})


class TrashDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        obj = _get(request.user, request.data.get('kind'), request.data.get('id'))
        delete_forever(obj)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TrashEmptyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        projects, chapters, references = _trashed(request.user)
        with transaction.atomic():
            for obj in [*chapters, *references]:
                delete_forever(obj)
            for project in projects:
                project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
