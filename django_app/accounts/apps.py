from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class AccountsConfig(AppConfig):
    name = "django_synergy.accounts"
    verbose_name = _("Accounts")