from decimal import Decimal

from django.db import migrations

FREE_SLUG = 'licence-classique'


def make_free(apps, schema_editor):
    """Le premier modèle du catalogue (Mémoire de Licence — Classique) devient gratuit."""
    apps.get_model('modeles', 'MemoirTemplate').objects.filter(slug=FREE_SLUG).update(price=Decimal('0'))


def restore_price(apps, schema_editor):
    from django.conf import settings
    apps.get_model('modeles', 'MemoirTemplate').objects.filter(slug=FREE_SLUG).update(price=Decimal(settings.MODELE_PRICE))


class Migration(migrations.Migration):
    dependencies = [('modeles', '0004_price_5000')]
    operations = [migrations.RunPython(make_free, restore_price)]
