"""Table du cache partagé (compteurs de limitation et de verrouillage des comptes).

Équivaut à « python manage.py createcachetable » : ne fait rien si le cache n'est pas en base
(développement, tests) ou si la table existe déjà.
"""
from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps, schema_editor):
    call_command('createcachetable', database=schema_editor.connection.alias, verbosity=0)


class Migration(migrations.Migration):
    dependencies = [('users', '0002_user_academic_title_user_department_and_more')]
    operations = [migrations.RunPython(create_cache_table, migrations.RunPython.noop)]
