"""Celery tasks for Discord Onboarding."""

import logging

from celery import shared_task
from celery.schedules import crontab

from allianceauth.services.modules.discord.models import DiscordUser
from allianceauth.services.modules.discord.tasks import update_groups, update_nickname

from .models import OnboardingToken

logger = logging.getLogger(__name__)


@shared_task
def process_completed_onboarding(token_id):
    """Process a completed onboarding by updating Discord roles and nickname."""

    try:
        token = OnboardingToken.objects.get(id=token_id)

        if not token.used or not token.user:
            logger.warning(f"Token {token_id} is not properly completed")
            return

        # Check if Discord user exists
        try:
            DiscordUser.objects.get(user=token.user)

            # Update groups (roles) for the user
            update_groups.delay(token.user.pk)
            logger.info(f"Queued group update for user {token.user}")

            # Update nickname for the user
            update_nickname.delay(token.user.pk)
            logger.info(f"Queued nickname update for user {token.user}")

        except DiscordUser.DoesNotExist:
            logger.error(
                f"DiscordUser not found for user {token.user} after onboarding completion"
            )

    except OnboardingToken.DoesNotExist:
        logger.error(f"OnboardingToken {token_id} not found")
    except Exception as e:
        logger.error(f"Error processing completed onboarding for token {token_id}: {e}")


@shared_task
def cleanup_expired_tokens():
    """Clean up expired and old onboarding tokens."""

    from django.utils import timezone
    from datetime import timedelta

    # Delete tokens older than 24 hours
    cutoff_date = timezone.now() - timedelta(hours=24)

    expired_count = OnboardingToken.objects.filter(
        created_at__lt=cutoff_date
    ).count()

    OnboardingToken.objects.filter(
        created_at__lt=cutoff_date
    ).delete()

    logger.info(f"Cleaned up {expired_count} expired onboarding tokens")
    return expired_count


# Periodic task configuration (add to CELERYBEAT_SCHEDULE in settings)
CELERYBEAT_SCHEDULE = {
    'discord_onboarding_cleanup': {
        'task': 'discord_onboarding.tasks.cleanup_expired_tokens',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
}
