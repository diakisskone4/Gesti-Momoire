# projects/management/commands/cleanup_archived.py
from django.core.management.base import BaseCommand
from django.utils.timezone import now, timedelta
from projects.models import Project

class Command(BaseCommand):
    help = 'Supprime les projets archivés depuis plus de 90 jours'

    def handle(self, *args, **kwargs):
        threshold = now() - timedelta(days=90)
        deleted_count, _ = Project.objects.filter(archived_at__lt=threshold).delete()
        self.stdout.write(self.style.SUCCESS(f'{deleted_count} projets supprimés'))