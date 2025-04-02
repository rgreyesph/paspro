from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments'
    verbose_name = _("Payments")

    def ready(self):
        """ Import and connect signals when the app is ready. """
        try:
            import payments.signals # noqa F401: Import signals to connect them
        except ImportError:
            pass