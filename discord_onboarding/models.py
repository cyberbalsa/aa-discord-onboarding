import uuid
from datetime import timedelta

from allianceauth.eveonline.models import EveCharacter
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class DiscordAuthRequest(models.Model):
    """
    Tracks pending Discord authentication requests with unique tokens
    """

    discord_user_id = models.BigIntegerField()
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Optional fields for tracking
    guild_id = models.BigIntegerField(null=True, blank=True)
    requested_by_admin = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="admin_discord_auth_requests",
    )

    # Result tracking
    auth_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="discord_auth_requests",
    )
    eve_character = models.ForeignKey(
        EveCharacter, null=True, blank=True, on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = "Discord Auth Request"
        verbose_name_plural = "Discord Auth Requests"
        indexes = [
            models.Index(fields=["discord_user_id"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["expires_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.completed and not self.is_expired

    def complete_auth(self, user, eve_character):
        """Mark the auth request as completed"""
        self.completed = True
        self.completed_at = timezone.now()
        self.auth_user = user
        self.eve_character = eve_character
        self.save()

    def __str__(self):
        return f"Discord Auth Request for {self.discord_user_id} - {self.token}"


class DiscordOnboardingConfiguration(models.Model):
    """
    Singleton configuration model for Discord onboarding settings
    """

    # Welcome message settings
    send_welcome_dm = models.BooleanField(
        default=True, help_text="Send welcome DM to new Discord members"
    )
    welcome_message_template = models.TextField(
        default=(
            "Welcome to our Discord server! 🎉\n\n"
            "To complete your registration and get access to all channels, "
            "please authenticate with EVE Online by clicking the link below:\n\n"
            "{auth_link}\n\n"
            "This link is valid for 24 hours. If you need a new link, "
            "use the `/auth` command in any channel."
        ),
        help_text=(
            "Template for welcome DM. Use {auth_link} placeholder "
            "for the authentication URL"
        ),
    )

    # Auto-role assignment
    auto_assign_authenticated_role = models.BooleanField(
        default=True,
        help_text="Automatically assign authenticated role after successful EVE SSO",
    )

    # Admin settings
    admin_role_ids = models.TextField(
        blank=True,
        help_text=(
            "Comma-separated list of Discord role IDs that can use admin auth commands"
        ),
    )

    # Rate limiting
    max_requests_per_user_per_day = models.IntegerField(
        default=5, help_text="Maximum auth requests per Discord user per day"
    )

    class Meta:
        verbose_name = "Discord Onboarding Configuration"
        verbose_name_plural = "Discord Onboarding Configuration"

    def save(self, *args, **kwargs):
        # Ensure only one configuration exists
        if not self.pk and DiscordOnboardingConfiguration.objects.exists():
            raise ValueError("Only one Discord Onboarding Configuration can exist")
        self.pk = self.id = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        """Get or create the configuration instance"""
        config, created = cls.objects.get_or_create(id=1)
        return config

    def get_admin_role_ids(self):
        """Get list of admin role IDs"""
        if not self.admin_role_ids:
            return []
        return [
            int(role_id.strip())
            for role_id in self.admin_role_ids.split(",")
            if role_id.strip()
        ]

    def __str__(self):
        return "Discord Onboarding Configuration"


class DiscordOnboardingStats(models.Model):
    """
    Statistics tracking for Discord onboarding
    """

    date = models.DateField(unique=True)

    # Counters
    auth_requests_created = models.IntegerField(default=0)
    auth_requests_completed = models.IntegerField(default=0)
    auth_requests_expired = models.IntegerField(default=0)

    # User metrics
    new_discord_members = models.IntegerField(default=0)
    successful_authentications = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Discord Onboarding Stats"
        verbose_name_plural = "Discord Onboarding Stats"
        ordering = ["-date"]

    @classmethod
    def get_today_stats(cls):
        """Get or create today's stats"""
        today = timezone.now().date()
        stats, created = cls.objects.get_or_create(date=today)
        return stats

    def __str__(self):
        return f"Discord Onboarding Stats for {self.date}"
