"""Celery tasks for Discord Onboarding."""

import logging

from celery import shared_task
from celery.schedules import crontab

from allianceauth.services.modules.discord.models import DiscordUser
from allianceauth.services.modules.discord.tasks import update_groups, update_nickname

from .models import OnboardingToken, AutoKickSchedule
from .app_settings import (
    DISCORD_ONBOARDING_AUTO_KICK_ENABLED,
    DISCORD_ONBOARDING_REMINDERS_ENABLED,
    DISCORD_ONBOARDING_KICK_LOG_CHANNEL_ID,
    DISCORD_ONBOARDING_KICK_GOODBYE_MESSAGE,
    DISCORD_ONBOARDING_BASE_URL
)

from aadiscordbot.app_settings import get_site_url

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


@shared_task
def send_onboarding_reminder(schedule_id):
    """Send a reminder DM with a fresh auth link to an unauthenticated user."""

    if not DISCORD_ONBOARDING_REMINDERS_ENABLED:
        logger.debug("Onboarding reminders are disabled")
        return

    try:
        schedule = AutoKickSchedule.objects.get(id=schedule_id, is_active=True)
    except AutoKickSchedule.DoesNotExist:
        logger.warning(f"AutoKickSchedule {schedule_id} not found or inactive")
        return

    # Check if user has authenticated since schedule was created
    if OnboardingToken.objects.filter(discord_id=schedule.discord_id, used=True).exists():
        logger.info(f"User {schedule.discord_username} has authenticated, deactivating schedule")
        schedule.deactivate()
        return

    # Create a fresh onboarding token
    try:
        token = OnboardingToken.objects.create(
            discord_id=schedule.discord_id,
            discord_username=schedule.discord_username
        )

        # Create onboarding URL
        base_url = DISCORD_ONBOARDING_BASE_URL or get_site_url()
        onboarding_url = f"{base_url}/discord-onboarding/start/{token.token}/"

        # Create reminder message
        reminder_number = schedule.reminder_count + 1
        message = f"**🔔 Authentication Reminder #{reminder_number} 🔔**"
        
        embed_data = {
            "title": "⏰ Authentication Reminder ⏰",
            "description": (
                f"# 🔐 **ACTION REQUIRED** 🔐\n\n"
                f"You still need to authenticate your Discord account with our Alliance Auth system.\n\n"
                f"**Time remaining:** You have until **{schedule.kick_scheduled_at.strftime('%Y-%m-%d %H:%M UTC')}** "
                f"to complete authentication, or you will be automatically removed from the server.\n\n"
            ),
            "color": 0xFF6B35,  # Orange color for warning
            "fields": [
                {
                    "name": "**👇 CLICK THE LINK BELOW TO AUTHENTICATE NOW 👇**",
                    "value": f"🚀 [**🔗 AUTHENTICATE NOW**]({onboarding_url}) 🚀\n\n",
                    "inline": False
                },
                {
                    "name": "❓ What happens if I don't authenticate?",
                    "value": (
                        "• You will be automatically removed from the server\n"
                        "• You can rejoin anytime and authenticate then\n"
                        "• No penalties - just complete the process when ready"
                    ),
                    "inline": False
                }
            ],
            "footer": {
                "text": f"This is reminder #{reminder_number}. Link expires in 1 hour."
            }
        }

        # Send DM via Discord bot task system
        from aadiscordbot import tasks as discord_tasks
        discord_tasks.send_direct_message_by_discord_id.delay(
            schedule.discord_id,  # discord_user_id as positional
            "",  # message as positional (empty since embed has content)
            embed=embed_data  # embed as keyword
        )

        # Mark reminder as sent
        schedule.mark_reminder_sent()
        
        logger.info(f"Sent reminder #{reminder_number} to {schedule.discord_username} (ID: {schedule.discord_id})")

    except Exception as e:
        logger.error(f"Error sending reminder to {schedule.discord_username}: {e}")


@shared_task
def auto_kick_unauthenticated_user(schedule_id):
    """Auto-kick an unauthenticated user after the timeout period."""

    if not DISCORD_ONBOARDING_AUTO_KICK_ENABLED:
        logger.debug("Auto-kick is disabled")
        return

    try:
        schedule = AutoKickSchedule.objects.get(id=schedule_id, is_active=True)
    except AutoKickSchedule.DoesNotExist:
        logger.warning(f"AutoKickSchedule {schedule_id} not found or inactive")
        return

    # Final check if user has authenticated
    if OnboardingToken.objects.filter(discord_id=schedule.discord_id, used=True).exists():
        logger.info(f"User {schedule.discord_username} authenticated before kick, deactivating schedule")
        schedule.deactivate()
        return

    try:
        # Send goodbye DM first
        goodbye_embed = {
            "title": "👋 Goodbye from our Discord Server",
            "description": DISCORD_ONBOARDING_KICK_GOODBYE_MESSAGE,
            "color": 0xFF0000,  # Red color
            "footer": {
                "text": "You're welcome to rejoin anytime and complete authentication then!"
            }
        }

        from aadiscordbot import tasks as discord_tasks
        discord_tasks.send_direct_message_by_discord_id.delay(
            schedule.discord_id,  # discord_user_id as positional
            "",  # message as positional (empty since embed has content)
            embed=goodbye_embed  # embed as keyword
        )

        # Kick user from guild
        kick_user_from_guild.delay(schedule.guild_id, schedule.discord_id, "Failed to authenticate within required timeframe")

        # Log the kick if channel is configured
        if DISCORD_ONBOARDING_KICK_LOG_CHANNEL_ID:
            log_auto_kick.delay(schedule_id)

        # Deactivate the schedule
        schedule.deactivate()

        logger.info(f"Auto-kicked user {schedule.discord_username} (ID: {schedule.discord_id}) from guild {schedule.guild_id}")

    except Exception as e:
        logger.error(f"Error auto-kicking user {schedule.discord_username}: {e}")


@shared_task 
def kick_user_from_guild(guild_id, user_id, reason):
    """Kick a user from a Discord guild."""
    
    try:
        from aadiscordbot import tasks as discord_tasks
        
        # Use the bot's task system to kick the user
        discord_tasks.run_task_function.delay(
            function='discord_onboarding.bot_tasks.kick_user_from_guild',
            task_args=[guild_id, user_id, reason],
            task_kwargs={}
        )
        
    except Exception as e:
        logger.error(f"Error queuing kick for user {user_id} from guild {guild_id}: {e}")


@shared_task
def log_auto_kick(schedule_id):
    """Log an auto-kick event to the configured channel."""

    if not DISCORD_ONBOARDING_KICK_LOG_CHANNEL_ID:
        return

    try:
        schedule = AutoKickSchedule.objects.get(id=schedule_id)
    except AutoKickSchedule.DoesNotExist:
        logger.warning(f"AutoKickSchedule {schedule_id} not found for logging")
        return

    try:
        log_embed = {
            "title": "🚪 Auto-Kick Event",
            "description": f"User **{schedule.discord_username}** was automatically removed from the server",
            "color": 0x808080,  # Gray color
            "fields": [
                {
                    "name": "Discord ID",
                    "value": str(schedule.discord_id),
                    "inline": True
                },
                {
                    "name": "Joined At", 
                    "value": schedule.joined_at.strftime('%Y-%m-%d %H:%M UTC'),
                    "inline": True
                },
                {
                    "name": "Reminders Sent",
                    "value": str(schedule.reminder_count),
                    "inline": True
                },
                {
                    "name": "Reason",
                    "value": "Failed to authenticate within required timeframe",
                    "inline": False
                }
            ],
            "timestamp": schedule.kick_scheduled_at.isoformat()
        }

        from aadiscordbot import tasks as discord_tasks
        discord_tasks.send_channel_message_by_discord_id.delay(
            DISCORD_ONBOARDING_KICK_LOG_CHANNEL_ID,  # channel_id as positional  
            "",  # message as positional (empty since embed has content)
            embed=log_embed  # embed as keyword
        )

        logger.info(f"Logged auto-kick event for {schedule.discord_username} to channel {DISCORD_ONBOARDING_KICK_LOG_CHANNEL_ID}")

    except Exception as e:
        logger.error(f"Error logging auto-kick event: {e}")



@shared_task
def process_auto_kick_schedules():
    """Process all active auto-kick schedules for reminders and kicks."""

    if not DISCORD_ONBOARDING_AUTO_KICK_ENABLED:
        return

    from django.utils import timezone

    # Process users due for reminders
    if DISCORD_ONBOARDING_REMINDERS_ENABLED:
        reminder_schedules = AutoKickSchedule.objects.filter(
            is_active=True
        ).select_related()

        reminder_count = 0
        for schedule in reminder_schedules:
            if schedule.is_due_for_reminder():
                send_onboarding_reminder.delay(schedule.id)
                reminder_count += 1

        if reminder_count > 0:
            logger.info(f"Queued {reminder_count} reminder messages")

    # Process users due for kicks
    kick_schedules = AutoKickSchedule.objects.filter(
        is_active=True,
        kick_scheduled_at__lte=timezone.now()
    )

    kick_count = 0
    for schedule in kick_schedules:
        if schedule.is_due_for_kick():
            auto_kick_unauthenticated_user.delay(schedule.id)
            kick_count += 1

    if kick_count > 0:
        logger.info(f"Queued {kick_count} auto-kick actions")

    return f"Processed {reminder_count} reminders and {kick_count} kicks"


# Periodic task configuration (add to CELERYBEAT_SCHEDULE in settings)
CELERYBEAT_SCHEDULE = {
    'discord_onboarding_cleanup': {
        'task': 'discord_onboarding.tasks.cleanup_expired_tokens',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
    'discord_onboarding_auto_kick_processor': {
        'task': 'discord_onboarding.tasks.process_auto_kick_schedules',
        'schedule': crontab(minute='*/15'),  # Run every 15 minutes
    },
}
