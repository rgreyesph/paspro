from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _ # Import gettext_lazy

class PersonsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'persons'
    verbose_name = _("Persons & Contacts") # Set a user-friendly name