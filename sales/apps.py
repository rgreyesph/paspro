from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class SalesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sales'
    verbose_name = _("Sales Management")

    def ready(self):
        """
        Import and connect signals when the application is ready.
        This ensures that the signal handlers are registered correctly.
        """
        try:
            import sales.signals # noqa F401: Import signals to connect them
        except ImportError:
            pass # Handle cases where signals.py might not exist initially etc.