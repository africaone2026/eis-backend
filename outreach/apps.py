from django.apps import AppConfig


class OutreachConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'outreach'
    verbose_name = 'Executive Outreach'
    
    def ready(self):
        import outreach.signals  # noqa
