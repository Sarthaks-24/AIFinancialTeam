from django.apps import AppConfig


class NexusConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "nexus"
    verbose_name = "Nexus Orchestration"

    def ready(self):
        # Import specialists so @register_specialist runs.
        from nexus import specialists  # noqa: F401
