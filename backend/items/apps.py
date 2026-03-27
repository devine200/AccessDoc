from django.apps import AppConfig


class ItemsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "items"

    def ready(self) -> None:
        import items.signals  # noqa: F401
