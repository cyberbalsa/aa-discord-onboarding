"""Discord bot tasks for onboarding auto-kick functionality."""

import logging

logger = logging.getLogger(__name__)


async def kick_user_from_guild(bot, guild_id, user_id, reason):
    """Bot task to kick a user from a Discord guild."""
    
    try:
        guild = bot.get_guild(int(guild_id))
        if not guild:
            logger.error(f"Guild {guild_id} not found")
            return False

        member = guild.get_member(int(user_id))
        if not member:
            logger.warning(f"Member {user_id} not found in guild {guild_id} (may have already left)")
            return False

        # Check if bot has permission to kick
        if not guild.me.guild_permissions.kick_members:
            logger.error(f"Bot lacks kick permissions in guild {guild_id}")
            return False

        # Check if we can kick this member (can't kick server owner or higher role)
        if member.id == guild.owner_id:
            logger.error(f"Cannot kick server owner {user_id}")
            return False

        if member.top_role >= guild.me.top_role:
            logger.error(f"Cannot kick member {user_id} with higher or equal role")
            return False

        # Perform the kick
        await member.kick(reason=reason)
        logger.info(f"Successfully kicked user {user_id} from guild {guild_id}: {reason}")
        return True

    except Exception as e:
        logger.error(f"Error kicking user {user_id} from guild {guild_id}: {e}")
        return False


async def check_user_in_guild(bot, guild_id, user_id):
    """Check if a user is still in the guild."""
    
    try:
        guild = bot.get_guild(int(guild_id))
        if not guild:
            return False

        member = guild.get_member(int(user_id))
        return member is not None

    except Exception as e:
        logger.error(f"Error checking user {user_id} in guild {guild_id}: {e}")
        return False


async def send_reminder_with_guild_context(bot, schedule_id, onboarding_url, reminder_number, kick_time):
    """Send reminder DM with guild name context."""
    
    try:
        from discord_onboarding.models import AutoKickSchedule
        schedule = AutoKickSchedule.objects.get(id=schedule_id)
        
        # Get guild name
        guild = bot.get_guild(int(schedule.guild_id))
        guild_name = guild.name if guild else "the Discord server"
        
        embed_data = {
            "title": f"{guild_name} Authentication Reminder #{reminder_number}",
            "description": (
                f"# **ACTION REQUIRED**\n\n"
                f"You still need to authenticate your Discord account to maintain access to **{guild_name}**.\n\n"
                f"**Time remaining:** You have until **{kick_time}** "
                f"to complete authentication, or you will be automatically removed from the server.\n\n"
            ),
            "color": 0xFF6B35,  # Orange color for warning
            "fields": [
                {
                    "name": "**CLICK THE LINK BELOW TO AUTHENTICATE NOW**",
                    "value": f"[**AUTHENTICATE NOW**]({onboarding_url})\n\n",
                    "inline": False
                },
                {
                    "name": "What happens if I don't authenticate?",
                    "value": (
                        f"• You will be automatically removed from **{guild_name}**\n"
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

        # Send the DM
        user_object = await bot.fetch_user(schedule.discord_id)
        if user_object.can_send():
            await user_object.create_dm()
            from discord import Embed
            embed = Embed.from_dict(embed_data)
            await user_object.send("", embed=embed)
            logger.info(f"Sent reminder #{reminder_number} to {schedule.discord_username} with {guild_name} context")
            return True
        else:
            logger.error(f"Unable to DM user {schedule.discord_id}")
            return False

    except Exception as e:
        logger.error(f"Error sending reminder with guild context: {e}")
        return False


async def send_goodbye_with_guild_context(bot, schedule_id, goodbye_message):
    """Send goodbye DM with guild name context."""
    
    try:
        from discord_onboarding.models import AutoKickSchedule
        schedule = AutoKickSchedule.objects.get(id=schedule_id)
        
        # Get guild name
        guild = bot.get_guild(int(schedule.guild_id))
        guild_name = guild.name if guild else "the Discord server"
        
        goodbye_embed = {
            "title": f"Goodbye from {guild_name}",
            "description": goodbye_message,
            "color": 0xFF0000,  # Red color
            "footer": {
                "text": f"You're welcome to rejoin {guild_name} anytime and complete authentication then!"
            }
        }

        # Send the DM
        user_object = await bot.fetch_user(schedule.discord_id)
        if user_object.can_send():
            await user_object.create_dm()
            from discord import Embed
            embed = Embed.from_dict(goodbye_embed)
            await user_object.send("", embed=embed)
            logger.info(f"Sent goodbye message to {schedule.discord_username} from {guild_name}")
            return True
        else:
            logger.error(f"Unable to send goodbye DM to user {schedule.discord_id}")
            return False

    except Exception as e:
        logger.error(f"Error sending goodbye with guild context: {e}")
        return False