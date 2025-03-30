from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments'
    verbose_name = _("Payments")

    # No signals defined in this app *yet*
    # def ready(self):
    #     import payments.signals