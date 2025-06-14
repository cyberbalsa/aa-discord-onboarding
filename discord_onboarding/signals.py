from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import DiscordAuthRequest, DiscordOnboardingStats


@receiver(post_save, sender=DiscordAuthRequest)
def update_stats_on_auth_request(sender, instance, created, **kwargs):
    """Update daily stats when auth requests are created or completed"""

    stats = DiscordOnboardingStats.get_today_stats()

    if created:
        # New auth request created
        stats.auth_requests_created += 1
        stats.save()

    elif instance.completed and instance.completed_at:
        # Auth request completed
        # Check if it was completed today
        if instance.completed_at.date() == timezone.now().date():
            completion_stats = DiscordOnboardingStats.get_today_stats()
            completion_stats.auth_requests_completed += 1
            completion_stats.successful_authentications += 1
            completion_stats.save()
