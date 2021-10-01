from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DevicesConfig(AppConfig):
    name = 'django_synergy.devices'
    verbose_name = _("Devices")
