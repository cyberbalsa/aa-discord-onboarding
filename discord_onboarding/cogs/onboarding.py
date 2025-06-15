"""Discord Onboarding Cog."""

import logging

import discord
from discord.colour import Color
from discord.embeds import Embed
from discord.ext import commands
from discord.commands import SlashCommandGroup

from aadiscordbot.app_settings import get_site_url
from aadiscordbot import app_settings as bot_settings
from allianceauth.services.modules.discord.models import DiscordUser

from ..app_settings import (
    DISCORD_ONBOARDING_ADMIN_ROLES, 
    DISCORD_ONBOARDING_BASE_URL,
    DISCORD_ONBOARDING_AUTO_KICK_ENABLED
)
from ..models import OnboardingToken, AutoKickSchedule

logger = logging.getLogger(__name__)


class OnboardingCog(commands.Cog):
    """
    Discord Onboarding Cog for Alliance Auth integration
    """

    def __init__(self, bot):
        self.bot = bot
        logger.info("OnboardingCog initialized")

    admin_commands = SlashCommandGroup(
        "onboarding-admin",
        "Discord Onboarding Admin Commands",
        guild_ids=bot_settings.get_all_servers()
    )

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Send onboarding DM when a user joins the server."""

        if member.bot:
            return  # Don't send DMs to bots

        try:
            # Create onboarding token
            username = (
                f"{member.name}#{member.discriminator}"
                if member.discriminator != '0'
                else f"@{member.name}"
            )
            token = OnboardingToken.objects.create(
                discord_id=member.id,
                discord_username=username
            )

            # Create auto-kick schedule if enabled
            if DISCORD_ONBOARDING_AUTO_KICK_ENABLED:
                from django.utils import timezone
                try:
                    AutoKickSchedule.objects.create(
                        discord_id=member.id,
                        discord_username=username,
                        guild_id=member.guild.id,
                        joined_at=timezone.now()
                    )
                    logger.info(f"Created auto-kick schedule for {username} (ID: {member.id})")
                except Exception as e:
                    logger.error(f"Failed to create auto-kick schedule for {username}: {e}")

            # Create onboarding URL
            base_url = DISCORD_ONBOARDING_BASE_URL or get_site_url()
            onboarding_url = f"{base_url}/discord-onboarding/start/{token.token}/"

            # Create embed for DM
            embed = Embed(
                title=f"🎉 Welcome to {member.guild.name}! 🎉",
                description=(
                    "# 🔐 **AUTHENTICATION REQUIRED** 🔐\n\n"
                    f"To gain access to all channels and features in **{member.guild.name}**, you need to link "
                    "your Discord account with our Alliance Auth system.\n\n"
                ),
                color=Color.gold()
            )

            embed.add_field(
                name="**👇 CLICK THE LINK BELOW TO GET STARTED 👇**",
                value=(
                    f"\n\n 🚀 [# **🔗 START AUTHENTICATION NOW**]({onboarding_url}) 🚀\n\n"
                ),
                inline=False
            )

            embed.add_field(
                name="❓ What happens next?",
                value=(
                    "• You'll be redirected to EVE Online SSO to verify your identity\n"
		    "• **No Private EVE Data is gathered, only public data**\n"
                    "• Your Discord account will be linked to your EVE character\n"
                    "• You'll automatically receive appropriate roles and access"
                ),
                inline=False
            )

            embed.add_field(
                name="💬 Need Help?",
                value=(
                    f"If you have any issues with {member.guild.name} authentication, please contact an administrator or use the "
                    "`/bind` command to get a new authentication link."
                ),
                inline=False
            )

            embed.set_footer(text="This link will expire in 1 hour for security reasons.")

            # Send DM to the user
            try:
                await member.send(embed=embed)
                logger.info(
                    f"Sent onboarding DM to {member.name}#{member.discriminator} (ID: {member.id})"
                )
            except discord.Forbidden:
                logger.warning(
                    f"Could not send DM to {member.name}#{member.discriminator} "
                    f"(ID: {member.id}) - DMs disabled"
                )
                # TODO: Maybe send a message in a welcome channel instead?
            except discord.HTTPException as e:
                logger.error(
                    f"Failed to send DM to {member.name}#{member.discriminator} "
                    f"(ID: {member.id}): {e}"
                )

        except Exception as e:
            logger.error(
                f"Error in on_member_join for {member.name}#{member.discriminator} "
                f"(ID: {member.id}): {e}"
            )

    @commands.slash_command(
        name='bind',
        description='Get an authentication link to link your Discord account'
    )
    async def bind_self(self, ctx: discord.ApplicationContext):
        """Allow users to get their own authentication link."""

        try:
            # Create or get existing token for this user
            try:
                # Try to get an existing valid token
                token = OnboardingToken.objects.filter(
                    discord_id=ctx.author.id,
                    used=False
                ).order_by('-created_at').first()

                if token and not token.is_expired():
                    # Use existing valid token
                    pass
                else:
                    # Create new token
                    username = (
                        f"{ctx.author.name}#{ctx.author.discriminator}"
                        if ctx.author.discriminator != '0'
                        else f"@{ctx.author.name}"
                    )
                    token = OnboardingToken.objects.create(
                        discord_id=ctx.author.id,
                        discord_username=username
                    )
            except Exception as e:
                logger.error(f"Error creating onboarding token for {ctx.author.id}: {e}")
                await ctx.respond(
                    "❌ An error occurred while creating your authentication link. "
                    "Please try again later.",
                    ephemeral=True
                )
                return

            # Create onboarding URL
            base_url = DISCORD_ONBOARDING_BASE_URL or get_site_url()
            onboarding_url = f"{base_url}/discord-onboarding/start/{token.token}/"

            # Create embed for response
            embed = Embed(
                title="🔗 Your Personal Authentication Link",
                description=(
                    "# 🔐 **AUTHENTICATION LINK READY** 🔐\n\n"
                ),
                color=Color.green()
            )

            embed.add_field(
                name="**👇 CLICK THE LINK BELOW TO AUTHENTICATE 👇**",
                value=(
                    f"🚀 [**🔗 CLICK HERE TO AUTHENTICATE**]({onboarding_url}) 🚀\n\n"
                ),
                inline=False
            )

            embed.set_footer(
                text="This link will expire in 1 hour. Only you can see this message."
            )

            await ctx.respond(embed=embed, ephemeral=True)
            logger.info(
                f"Sent bind link to {ctx.author.name}#{ctx.author.discriminator} "
                f"(ID: {ctx.author.id})"
            )

        except Exception as e:
            logger.error(f"Error in bind_self command for {ctx.author.id}: {e}")
            await ctx.respond("❌ An error occurred. Please try again later.", ephemeral=True)

    @commands.slash_command(
        name='auth-user',
        description='Send an authentication link to another user (Admin only)'
    )
    async def auth_user(self, ctx: discord.ApplicationContext, user: discord.Member):
        """Allow admins to send authentication links to other users."""

        # Check if user has admin permissions
        if not self._is_admin(ctx.author):
            await ctx.respond(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return

        if user.bot:
            await ctx.respond(
                "❌ Cannot send authentication links to bots.",
                ephemeral=True
            )
            return

        try:
            # Create onboarding token
            username = (
                f"{user.name}#{user.discriminator}"
                if user.discriminator != '0'
                else f"@{user.name}"
            )
            token = OnboardingToken.objects.create(
                discord_id=user.id,
                discord_username=username
            )

            # Create onboarding URL
            base_url = DISCORD_ONBOARDING_BASE_URL or get_site_url()
            onboarding_url = f"{base_url}/discord-onboarding/start/{token.token}/"

            # Create embed for DM to target user
            embed = Embed(
                title=f"🛡️ {ctx.guild.name} Admin Authentication Request 🛡️",
                description=(
                    f"# 🔐 **AUTHENTICATION REQUIRED** 🔐\n\n"
                    f"An administrator ({ctx.author.mention}) from **{ctx.guild.name}** has sent you an authentication "
                    f"link to link your Discord account with Alliance Auth.\n\n"
                ),
                color=Color.orange()
            )

            embed.add_field(
                name="**👇 CLICK THE LINK BELOW TO GET STARTED 👇**",
                value=(
                    f" [**🔗 CLICK HERE TO AUTHENTICATE**]({onboarding_url}) \n\n"
                    f"⬆️ **Click the blue link above to get started** ⬆️"
                ),
                inline=False
            )

            embed.set_footer(text="This link will expire in 1 hour.")

            # Send DM to target user
            try:
                await user.send(embed=embed)

                # Confirm to admin
                await ctx.respond(
                    f"✅ Authentication link sent to {user.mention} via DM.",
                    ephemeral=True
                )
                logger.info(
                    f"Admin {ctx.author.name}#{ctx.author.discriminator} sent auth link to "
                    f"{user.name}#{user.discriminator}"
                )

            except discord.Forbidden:
                await ctx.respond(
                    f"❌ Could not send DM to {user.mention} - their DMs might be disabled.",
                    ephemeral=True
                )
                logger.warning(
                    f"Could not send admin-requested DM to {user.name}#{user.discriminator} "
                    f"(ID: {user.id})"
                )
            except discord.HTTPException as e:
                await ctx.respond(
                    f"❌ Failed to send DM to {user.mention}: {str(e)}",
                    ephemeral=True
                )
                logger.error(
                    f"Failed to send admin-requested DM to {user.name}#{user.discriminator} "
                    f"(ID: {user.id}): {e}"
                )

        except Exception as e:
            logger.error(f"Error in auth_user command for target {user.id}: {e}")
            await ctx.respond("❌ An error occurred. Please try again later.", ephemeral=True)

    @admin_commands.command(name='add_orphans_to_autokick', guild_ids=bot_settings.get_all_servers())
    async def add_orphans_to_autokick(self, ctx):
        """
        Add all unlinked Discord users in the server to the auto-kick timeline
        """
        # Check admin permissions using the same method as allianceauth-discordbot
        if ctx.author.id not in bot_settings.get_admins():
            return await ctx.respond("You do not have permission to use this command", ephemeral=True)

        if not DISCORD_ONBOARDING_AUTO_KICK_ENABLED:
            return await ctx.respond("❌ Auto-kick feature is not enabled", ephemeral=True)

        await ctx.defer()

        try:
            # Get all Discord members in the guild
            member_list = ctx.guild.members
            added_count = 0
            already_scheduled_count = 0
            bot_count = 0
            linked_count = 0

            # Batch queries for efficiency
            logger.info(f"Processing {len(member_list)} Discord members for auto-kick scheduling...")
            
            # Get all existing linked Discord user IDs in one query
            member_ids = [member.id for member in member_list if not member.bot]
            linked_user_ids = set(DiscordUser.objects.filter(uid__in=member_ids).values_list('uid', flat=True))
            
            # Get all existing active auto-kick schedule IDs in one query  
            existing_schedule_ids = set(AutoKickSchedule.objects.filter(
                discord_id__in=member_ids, 
                is_active=True
            ).values_list('discord_id', flat=True))

            # Prepare batch insert data
            schedules_to_create = []
            from django.utils import timezone
            from datetime import timedelta
            from ..app_settings import DISCORD_ONBOARDING_AUTO_KICK_TIMEOUT_HOURS
            
            current_time = timezone.now()
            kick_time = current_time + timedelta(hours=DISCORD_ONBOARDING_AUTO_KICK_TIMEOUT_HOURS)

            for member in member_list:
                # Skip bots
                if member.bot:
                    bot_count += 1
                    continue

                # Check if user is already linked to Alliance Auth
                if member.id in linked_user_ids:
                    linked_count += 1
                    continue

                # Check if user already has an active auto-kick schedule
                if member.id in existing_schedule_ids:
                    already_scheduled_count += 1
                    continue

                # Prepare auto-kick schedule for this orphaned user
                username = (
                    f"{member.name}#{member.discriminator}"
                    if member.discriminator != '0'
                    else f"@{member.name}"
                )
                
                schedules_to_create.append(AutoKickSchedule(
                    discord_id=member.id,
                    discord_username=username,
                    guild_id=ctx.guild.id,
                    joined_at=current_time,
                    kick_scheduled_at=kick_time  # Explicitly set the kick time
                ))

            # Batch create all schedules
            if schedules_to_create:
                try:
                    # Use bulk_create for efficiency with large datasets
                    AutoKickSchedule.objects.bulk_create(schedules_to_create, batch_size=1000)
                    added_count = len(schedules_to_create)
                    logger.info(f"Batch created {added_count} auto-kick schedules")
                except Exception as e:
                    logger.error(f"Failed to batch create auto-kick schedules: {e}")
                    # Fallback to individual creation if batch fails
                    for schedule in schedules_to_create:
                        try:
                            schedule.save()
                            added_count += 1
                        except Exception as individual_error:
                            logger.error(f"Failed to create schedule for {schedule.discord_username}: {individual_error}")

            # Create response embed
            embed = Embed(
                title="🚫 Auto-Kick Schedule Updated",
                description="Added unlinked Discord users to auto-kick timeline",
                color=Color.orange()
            )
            
            embed.add_field(name="✅ Added to Timeline", value=str(added_count), inline=True)
            embed.add_field(name="📅 Already Scheduled", value=str(already_scheduled_count), inline=True)
            embed.add_field(name="🔗 Already Linked", value=str(linked_count), inline=True)
            embed.add_field(name="🤖 Bots Skipped", value=str(bot_count), inline=True)
            embed.add_field(name="👥 Total Members", value=str(len(member_list)), inline=True)
            embed.add_field(name="⚡ Status", value="Complete", inline=True)

            await ctx.respond(embed=embed)

        except Exception as e:
            logger.error(f"Error in add_orphans_to_autokick command: {e}")
            await ctx.respond("❌ An error occurred while processing the command. Check logs for details.", ephemeral=True)

    @admin_commands.command(name='clear_autokick_timeline', guild_ids=bot_settings.get_all_servers()) 
    async def clear_autokick_timeline(self, ctx):
        """
        Clear the entire auto-kick timeline (delete all scheduled kicks)
        """
        # Check admin permissions using the same method as allianceauth-discordbot
        if ctx.author.id not in bot_settings.get_admins():
            return await ctx.respond("You do not have permission to use this command", ephemeral=True)

        await ctx.defer()

        try:
            # Get count of active schedules before clearing
            active_schedules = AutoKickSchedule.objects.filter(is_active=True)
            total_count = active_schedules.count()

            if total_count == 0:
                embed = Embed(
                    title="🟢 Auto-Kick Timeline",
                    description="Timeline is already empty - no active schedules found",
                    color=Color.green()
                )
                return await ctx.respond(embed=embed)

            # Delete all active schedules from database
            try:
                # Use bulk delete for efficiency
                deleted_count, _ = AutoKickSchedule.objects.filter(is_active=True).delete()
                logger.info(f"Bulk deleted {deleted_count} auto-kick schedules from database")
            except Exception as e:
                logger.error(f"Failed to bulk delete schedules: {e}")
                # Fallback to individual deletion
                deleted_count = 0
                for schedule in active_schedules:
                    try:
                        schedule.delete()
                        deleted_count += 1
                        logger.info(f"Deleted auto-kick schedule for {schedule.discord_username} (ID: {schedule.discord_id})")
                    except Exception as individual_error:
                        logger.error(f"Failed to delete schedule for {schedule.discord_username}: {individual_error}")

            # Create response embed
            embed = Embed(
                title="🗑️ Auto-Kick Timeline Purged",
                description="All scheduled auto-kicks have been permanently deleted",
                color=Color.red()
            )
            
            embed.add_field(name="📊 Total Found", value=str(total_count), inline=True)
            embed.add_field(name="🗑️ Deleted", value=str(deleted_count), inline=True)
            embed.add_field(name="❌ Failed", value=str(total_count - deleted_count), inline=True)
            
            if deleted_count > 0:
                embed.add_field(
                    name="ℹ️ Note", 
                    value="All auto-kick schedules have been permanently removed from the database. Users can still authenticate normally.",
                    inline=False
                )

            await ctx.respond(embed=embed)

        except Exception as e:
            logger.error(f"Error in clear_autokick_timeline command: {e}")
            await ctx.respond("❌ An error occurred while clearing the timeline. Check logs for details.", ephemeral=True)

    def _is_admin(self, member: discord.Member) -> bool:
        """Check if a member has admin permissions for this bot."""

        # Check if user has any of the configured admin roles
        if DISCORD_ONBOARDING_ADMIN_ROLES:
            member_role_ids = [role.id for role in member.roles]
            if any(role_id in member_role_ids for role_id in DISCORD_ONBOARDING_ADMIN_ROLES):
                return True

        # Check if user has Discord server admin permissions
        if member.guild_permissions.administrator:
            return True

        # Check if user has manage_server permission
        if member.guild_permissions.manage_guild:
            return True

        return False


def setup(bot):
    """Setup function called by the Discord bot."""
    logger.info("Loading Discord Onboarding cog...")
    bot.add_cog(OnboardingCog(bot))
    logger.info("Discord Onboarding cog loaded successfully!")
