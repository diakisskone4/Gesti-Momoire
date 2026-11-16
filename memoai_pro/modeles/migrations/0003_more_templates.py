from django.conf import settings
from django.db import migrations


def seed(apps, schema_editor):
    """Ajoute les nouveaux modèles du catalogue (rapport de stage, informatique, santé, agronomie...)."""
    from modeles.catalog import sync_catalog
    sync_catalog(apps.get_model('modeles', 'MemoirTemplate'), settings.MODELE_PRICE)


class Migration(migrations.Migration):
    dependencies = [('modeles', '0002_seed_catalog')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
