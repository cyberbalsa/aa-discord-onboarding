"""Models for Discord Onboarding."""

import secrets
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .app_settings import DISCORD_ONBOARDING_TOKEN_EXPIRY


class General(models.Model):
    """A meta model for app permissions."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("basic_access", "Can access Discord onboarding"),
            ("admin_access", "Can send auth requests to other users"),
        )


class OnboardingToken(models.Model):
    """Temporary tokens for Discord onboarding process."""

    token = models.CharField(max_length=64, unique=True, db_index=True)
    discord_id = models.BigIntegerField(help_text="Discord user ID")
    discord_username = models.CharField(
        max_length=100, help_text="Discord username for reference"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.CASCADE,
        help_text="Linked Alliance Auth user (after successful auth)"
    )

    class Meta:
        verbose_name = "Onboarding Token"
        verbose_name_plural = "Onboarding Tokens"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(48)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(
                seconds=DISCORD_ONBOARDING_TOKEN_EXPIRY
            )
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self):
        return not self.used and not self.is_expired()

    def __str__(self):
        status = 'used' if self.used else 'valid' if self.is_valid() else 'expired'
        return f"Token for {self.discord_username} ({status})"
