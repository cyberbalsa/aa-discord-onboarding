"""Discord Onboarding Cog."""

import logging

import discord
from discord.colour import Color
from discord.embeds import Embed
from discord.ext import commands

from aadiscordbot.app_settings import get_site_url

from ..app_settings import DISCORD_ONBOARDING_ADMIN_ROLES, DISCORD_ONBOARDING_BASE_URL
from ..models import OnboardingToken

logger = logging.getLogger(__name__)


class OnboardingCog(commands.Cog):
    """
    Discord Onboarding Cog for Alliance Auth integration
    """

    def __init__(self, bot):
        self.bot = bot

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

            # Create onboarding URL
            base_url = DISCORD_ONBOARDING_BASE_URL or get_site_url()
            onboarding_url = f"{base_url}/discord-onboarding/start/{token.token}/"

            # Create embed for DM
            embed = Embed(
                title="Welcome to our Discord Server!",
                description=(
                    "To gain access to all channels and features, you need to link "
                    "your Discord account with our Alliance Auth system."
                ),
                color=Color.blue()
            )

            embed.add_field(
                name="🚀 Get Started",
                value=(
                    f"Click the link below to authenticate with EVE Online and gain access:\n\n"
                    f"[**Start Authentication Process**]({onboarding_url})"
                ),
                inline=False
            )

            embed.add_field(
                name="❓ What happens next?",
                value=(
                    "• You'll be redirected to EVE Online SSO to verify your identity\n"
                    "• Your Discord account will be linked to your EVE character\n"
                    "• You'll automatically receive appropriate roles and access"
                ),
                inline=False
            )

            embed.add_field(
                name="💬 Need Help?",
                value=(
                    "If you have any issues, please contact an administrator or use the "
                    "`/auth` command to get a new authentication link."
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
        name='auth',
        description='Get an authentication link to link your Discord account'
    )
    async def auth_self(self, ctx: discord.ApplicationContext):
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
                title="🔗 Authentication Link",
                description=(
                    "Click the link below to authenticate with EVE Online and "
                    "link your Discord account:"
                ),
                color=Color.green()
            )

            embed.add_field(
                name="🚀 Authenticate Now",
                value=f"[**Click here to start authentication**]({onboarding_url})",
                inline=False
            )

            embed.set_footer(
                text="This link will expire in 1 hour. Only you can see this message."
            )

            await ctx.respond(embed=embed, ephemeral=True)
            logger.info(
                f"Sent auth link to {ctx.author.name}#{ctx.author.discriminator} "
                f"(ID: {ctx.author.id})"
            )

        except Exception as e:
            logger.error(f"Error in auth_self command for {ctx.author.id}: {e}")
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
                title="Authentication Request",
                description=(
                    f"An administrator ({ctx.author.mention}) has sent you an authentication "
                    f"link to link your Discord account with Alliance Auth."
                ),
                color=Color.blue()
            )

            embed.add_field(
                name="🚀 Get Started",
                value=f"[**Click here to authenticate**]({onboarding_url})",
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
    bot.add_cog(OnboardingCog(bot))
