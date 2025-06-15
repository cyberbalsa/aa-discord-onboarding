"""Django signals for Discord Onboarding."""

import logging

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import OnboardingToken
from .tasks import process_completed_onboarding
from .app_settings import DISCORD_ONBOARDING_BYPASS_EMAIL_VERIFICATION

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def activate_discord_onboarding_user(sender, instance, created, **kwargs):
    """Automatically activate users created through Discord onboarding when bypass is enabled."""
    
    if not created or not DISCORD_ONBOARDING_BYPASS_EMAIL_VERIFICATION:
        return
    
    # Check if this is a Discord onboarding session by looking for recent onboarding tokens
    # that are not yet used and could be for this user
    from django.utils import timezone
    from datetime import timedelta
    
    # Look for recent unused onboarding tokens (within the last 10 minutes)
    recent_time = timezone.now() - timedelta(minutes=10)
    recent_tokens = OnboardingToken.objects.filter(
        created_at__gte=recent_time,
        used=False
    )
    
    # If there are recent onboarding tokens, this might be a Discord onboarding user
    if recent_tokens.exists():
        # Also check if there's a session flag indicating Discord onboarding
        from django.core.cache import cache
        
        # Check for session-based flag (set during onboarding start)
        onboarding_sessions = []
        for i in range(10):  # Check last 10 possible session keys
            session_key = f"discord_onboarding_active_{i}"
            if cache.get(session_key):
                onboarding_sessions.append(session_key)
        
        if onboarding_sessions:
            logger.info(f"Activating user {instance.username} via Discord onboarding email bypass")
            instance.is_active = True
            instance.save(update_fields=['is_active'])
            # Clean up the session flags
            for session_key in onboarding_sessions:
                cache.delete(session_key)


@receiver(post_save, sender=OnboardingToken)
def onboarding_token_saved(sender, instance, created, **kwargs):
    """Handle when an onboarding token is saved."""

    if not created and instance.used and instance.user:
        # Token was just marked as used and linked to a user
        logger.info(
            f"Onboarding completed for user {instance.user} "
            f"(Discord ID: {instance.discord_id})"
        )

        # Queue the Discord sync task
        process_completed_onboarding.delay(instance.id)
