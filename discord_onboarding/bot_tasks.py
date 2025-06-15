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