from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class PurchasesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'purchases'
    verbose_name = _("Purchases & Expenses")

    def ready(self):
        """
        Import and connect signals when the application is ready.
        """
        try:
            import purchases.signals # noqa F401: Import signals to connect them
        except ImportError:
            pass