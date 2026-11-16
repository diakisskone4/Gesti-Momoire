from django.conf import settings
from django.core.management.base import BaseCommand

from modeles.catalog import CATALOG, sync_catalog
from modeles.models import MemoirTemplate


class Command(BaseCommand):
    help = 'Crée ou met à jour les modèles de mémoire à partir de modeles/catalog.py.'

    def handle(self, *args, **options):
        created = sync_catalog(MemoirTemplate, settings.MODELE_PRICE)
        self.stdout.write(self.style.SUCCESS(f'{len(CATALOG)} modèles synchronisés ({created} créés).'))
