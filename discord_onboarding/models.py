"""Models for Discord Onboarding."""

import secrets
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .app_settings import (
    DISCORD_ONBOARDING_TOKEN_EXPIRY,
    DISCORD_ONBOARDING_AUTO_KICK_TIMEOUT_HOURS,
    DISCORD_ONBOARDING_REMINDER_INTERVAL_HOURS
)


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


class AutoKickSchedule(models.Model):
    """Schedule for auto-kicking unauthenticated Discord users."""

    discord_id = models.BigIntegerField(unique=True, help_text="Discord user ID")
    discord_username = models.CharField(
        max_length=100, help_text="Discord username for reference"
    )
    guild_id = models.BigIntegerField(help_text="Discord guild ID where user joined")
    joined_at = models.DateTimeField(help_text="When the user joined the server")
    last_reminder_sent = models.DateTimeField(null=True, blank=True, help_text="Last time a reminder was sent")
    kick_scheduled_at = models.DateTimeField(help_text="When the user should be kicked")
    is_active = models.BooleanField(default=True, help_text="Whether the schedule is active")
    reminder_count = models.IntegerField(default=0, help_text="Number of reminders sent")

    class Meta:
        verbose_name = "Auto-Kick Schedule"
        verbose_name_plural = "Auto-Kick Schedules"
        indexes = [
            models.Index(fields=['kick_scheduled_at', 'is_active']),
            models.Index(fields=['last_reminder_sent', 'is_active']),
        ]

    def save(self, *args, **kwargs):
        if not self.kick_scheduled_at:
            self.kick_scheduled_at = self.joined_at + timedelta(
                hours=DISCORD_ONBOARDING_AUTO_KICK_TIMEOUT_HOURS
            )
        super().save(*args, **kwargs)

    def is_due_for_reminder(self):
        """Check if user is due for a reminder DM."""
        if not self.is_active:
            return False

        if not self.last_reminder_sent:
            # If no reminder sent yet, check if it's been at least the reminder interval since joining
            return timezone.now() >= self.joined_at + timedelta(
                hours=DISCORD_ONBOARDING_REMINDER_INTERVAL_HOURS
            )

        # Check if it's been at least the reminder interval since last reminder
        return timezone.now() >= self.last_reminder_sent + timedelta(
            hours=DISCORD_ONBOARDING_REMINDER_INTERVAL_HOURS
        )

    def is_due_for_kick(self):
        """Check if user is due to be kicked."""
        return self.is_active and timezone.now() >= self.kick_scheduled_at

    def mark_reminder_sent(self):
        """Mark that a reminder was sent."""
        self.last_reminder_sent = timezone.now()
        self.reminder_count += 1
        self.save()

    def deactivate(self):
        """Deactivate the schedule (user authenticated or was kicked)."""
        self.is_active = False
        self.save()

    def __str__(self):
        status = "active" if self.is_active else "inactive"
        return f"AutoKick for {self.discord_username} ({status})"
