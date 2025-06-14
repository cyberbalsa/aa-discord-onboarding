from django.apps import AppConfig


class DiscordOnboardingConfig(AppConfig):
    name = "discord_onboarding"
    label = "discord_onboarding"
    verbose_name = "Discord Onboarding"
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from . import signals  # noqa: F401
