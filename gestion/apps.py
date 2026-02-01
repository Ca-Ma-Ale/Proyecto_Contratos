from django.apps import AppConfig


class GestionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gestion'
    verbose_name = 'Gestión de Contratos'
    
    def ready(self):
        """Registrar señales cuando la app esté lista"""
        import gestion.signals  # noqa