from django.apps import AppConfig


class DiscordOnboardingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "discord_onboarding"
    verbose_name = "Discord Onboarding"

    def ready(self):
        # Import signals to ensure they're registered
        from . import signals  # noqa: F401
