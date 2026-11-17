from decimal import Decimal

from django.conf import settings
from django.db import migrations, models

OLD_PRICE = Decimal('15500')


def lower_prices(apps, schema_editor):
    """Passe les modèles encore au prix d'origine (15 500 FCFA) au nouveau prix (MODELE_PRICE, 5 000 FCFA).
    Un prix modifié à la main dans l'administration n'est pas touché. Les achats déjà payés gardent leur montant."""
    Template = apps.get_model('modeles', 'MemoirTemplate')
    Template.objects.filter(price=OLD_PRICE).update(price=Decimal(settings.MODELE_PRICE))


class Migration(migrations.Migration):
    dependencies = [('modeles', '0003_more_templates')]
    operations = [
        migrations.AlterField(
            model_name='memoirtemplate',
            name='price',
            field=models.DecimalField(decimal_places=2, default=Decimal('5000'), max_digits=10),
        ),
        migrations.RunPython(lower_prices, migrations.RunPython.noop),
    ]
