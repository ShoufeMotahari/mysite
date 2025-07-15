from django.apps import AppConfig


class EmailsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'emails'
    verbose_name = 'Email Broadcasting'

    def ready(self):
        # Import signals if you have any
        # import emails.signals
        pass