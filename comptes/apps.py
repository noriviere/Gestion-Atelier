from django.apps import AppConfig
from django.db.models.signals import post_migrate


class ComptesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "comptes"
    verbose_name = "Comptes et profils"

    def ready(self):
        from .roles import configurer_permissions

        post_migrate.connect(configurer_permissions, sender=self)
