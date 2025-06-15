"""Django signals for Discord Onboarding."""

import logging

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import OnboardingToken
from .tasks import process_completed_onboarding
from .app_settings import DISCORD_ONBOARDING_BYPASS_EMAIL_VERIFICATION

logger = logging.getLogger(__name__)

# Log that signals are being loaded
logger.info("Discord onboarding signals module loaded")


@receiver(post_save, sender=User)
def activate_discord_onboarding_user(sender, instance, created, **kwargs):
    """Automatically activate users created through Discord onboarding when bypass is enabled."""
    
    logger.info(f"POST_SAVE SIGNAL: User {instance.username}, created={created}, bypass_enabled={DISCORD_ONBOARDING_BYPASS_EMAIL_VERIFICATION}")
    
    if not created:
        return
        
    if not DISCORD_ONBOARDING_BYPASS_EMAIL_VERIFICATION:
        logger.info(f"Discord onboarding bypass disabled, skipping activation for {instance.username}")
        return
    
    # Check if this is a Discord onboarding session by looking for recent onboarding tokens
    # that are not yet used and could be for this user
    from django.utils import timezone
    from datetime import timedelta
    from django.core.cache import cache
    
    # Look for recent unused onboarding tokens (within the last 10 minutes)
    recent_time = timezone.now() - timedelta(minutes=10)
    recent_tokens = OnboardingToken.objects.filter(
        created_at__gte=recent_time,
        used=False
    )
    
    logger.debug(f"Found {recent_tokens.count()} recent unused onboarding tokens")
    
    # If there are recent onboarding tokens, this might be a Discord onboarding user
    if recent_tokens.exists():
        # Check for a simple cache flag indicating recent Discord onboarding activity
        try:
            onboarding_active = cache.get('discord_onboarding_active', False)
            logger.debug(f"Cache flag 'discord_onboarding_active' = {onboarding_active}")
            
            if onboarding_active:
                logger.info(f"Activating user {instance.username} via Discord onboarding email bypass")
                instance.is_active = True
                instance.save(update_fields=['is_active'])
                # Don't clear the flag immediately in case multiple users are onboarding
            else:
                # Fallback: if we have recent tokens but no cache flag, still activate
                # This handles cases where cache might not be working properly
                logger.info(f"Activating user {instance.username} via Discord onboarding email bypass (fallback - recent tokens found)")
                instance.is_active = True
                instance.save(update_fields=['is_active'])
        except Exception as e:
            logger.error(f"Error checking cache in signal handler: {e}")
            # Fallback activation if cache fails
            logger.info(f"Activating user {instance.username} via Discord onboarding email bypass (cache error fallback)")
            instance.is_active = True
            instance.save(update_fields=['is_active'])


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
