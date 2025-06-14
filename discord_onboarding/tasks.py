import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import DiscordAuthRequest, DiscordOnboardingStats

logger = logging.getLogger(__name__)


@shared_task
def send_auth_success_notification(discord_user_id, character_name, guild_id=None):
    """
    Send a success notification to Discord when authentication is completed
    """
    try:
        # Import here to avoid circular imports
        from aadiscordbot.tasks import send_direct_message

        message = (
            f"🎉 **Authentication Successful!**\n\n"
            f"Your Discord account has been successfully linked to **{character_name}**.\n\n"
            f"You now have access to all authenticated channels and features. Welcome aboard!"
        )

        send_direct_message.delay(user_id=discord_user_id, message=message)

        logger.info(
            f"Sent authentication success notification to Discord user {discord_user_id}"
        )

    except Exception as e:
        logger.error(f"Failed to send authentication success notification: {e}")


@shared_task
def send_welcome_auth_message(discord_user_id, guild_id, auth_url):
    """
    Send welcome message with authentication link to new Discord member
    """
    try:
        from aadiscordbot.tasks import send_direct_message

        from .models import DiscordOnboardingConfiguration

        config = DiscordOnboardingConfiguration.get_config()

        if not config.send_welcome_dm:
            return

        message = config.welcome_message_template.format(auth_link=auth_url)

        send_direct_message.delay(user_id=discord_user_id, message=message)

        logger.info(
            f"Sent welcome authentication message to Discord user {discord_user_id}"
        )

        # Update stats
        stats = DiscordOnboardingStats.get_today_stats()
        stats.new_discord_members += 1
        stats.save()

    except Exception as e:
        logger.error(f"Failed to send welcome authentication message: {e}")


@shared_task
def cleanup_expired_auth_requests():
    """
    Clean up expired authentication requests (run daily)
    """
    try:
        cutoff_date = timezone.now() - timedelta(
            days=7
        )  # Keep for 7 days for admin review

        expired_requests = DiscordAuthRequest.objects.filter(
            expires_at__lt=timezone.now(), completed=False, created_at__lt=cutoff_date
        )

        count = expired_requests.count()
        expired_requests.delete()

        logger.info(f"Cleaned up {count} expired authentication requests")

        # Update today's stats with expired count
        today_expired = DiscordAuthRequest.objects.filter(
            expires_at__lt=timezone.now(),
            expires_at__date=timezone.now().date(),
            completed=False,
        ).count()

        if today_expired > 0:
            stats = DiscordOnboardingStats.get_today_stats()
            stats.auth_requests_expired += today_expired
            stats.save()

    except Exception as e:
        logger.error(f"Failed to cleanup expired authentication requests: {e}")


@shared_task
def update_character_information(character_id):
    """
    Update EVE character information after authentication
    """
    try:
        from allianceauth.eveonline.models import EveCharacter

        character = EveCharacter.objects.get(character_id=character_id)
        character.update_character()

        logger.info(f"Updated character information for {character.character_name}")

    except EveCharacter.DoesNotExist:
        logger.warning(f"Character {character_id} not found for update")
    except Exception as e:
        logger.error(f"Failed to update character information for {character_id}: {e}")
