"""Django signals for Discord Onboarding."""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import OnboardingToken
from .tasks import process_completed_onboarding

logger = logging.getLogger(__name__)


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
