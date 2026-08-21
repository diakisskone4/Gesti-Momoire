from django.apps import AppConfig


class CollaborationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'collaborations'
    
    def ready(self):
        # Importer les signaux si nécessaire
        pass