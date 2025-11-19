from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HdhConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "high_desert_happenings.hdh"
    verbose_name = _("High Desert Happenings")
