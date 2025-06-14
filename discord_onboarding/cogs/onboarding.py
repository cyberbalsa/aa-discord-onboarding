import logging
from datetime import timedelta

import discord
from aadiscordbot.app_settings import get_site_url
from aadiscordbot.cogs.utils.decorators import sender_has_perm
from discord.ext import commands
from django.utils import timezone

logger = logging.getLogger(__name__)


class DiscordOnboardingCog(commands.Cog):
    """
    Discord onboarding cog for EVE Online authentication
    """

    def __init__(self, bot):
        self.bot = bot

    def _get_auth_url(self, token):
        """Generate authentication URL for a token"""
        base_url = get_site_url()
        return f"{base_url}/discord-onboarding/auth/{token}/"

    def _is_admin_user(self, user, guild):
        """Check if user has admin permissions for auth commands"""
        from discord_onboarding.models import DiscordOnboardingConfiguration

        try:
            config = DiscordOnboardingConfiguration.get_config()
            admin_role_ids = config.get_admin_role_ids()

            if not admin_role_ids:
                # If no admin roles configured, check for administrator permission
                member = guild.get_member(user.id)
                return member and member.guild_permissions.administrator

            # Check if user has any of the configured admin roles
            member = guild.get_member(user.id)
            if not member:
                return False

            user_role_ids = [role.id for role in member.roles]
            return any(role_id in user_role_ids for role_id in admin_role_ids)

        except Exception as e:
            logger.error(f"Error checking admin permissions: {e}")
            return False

    def _check_rate_limit(self, discord_user_id):
        """Check if user has exceeded rate limit for auth requests"""
        from discord_onboarding.models import (
            DiscordAuthRequest,
            DiscordOnboardingConfiguration,
        )

        try:
            config = DiscordOnboardingConfiguration.get_config()
            max_requests = config.max_requests_per_user_per_day

            # Count requests from last 24 hours
            cutoff_time = timezone.now() - timedelta(hours=24)
            recent_requests = DiscordAuthRequest.objects.filter(
                discord_user_id=discord_user_id, created_at__gte=cutoff_time
            ).count()

            return recent_requests < max_requests

        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow on error

    def _create_auth_request(self, discord_user_id, guild_id=None, admin_user=None):
        """Create a new authentication request"""
        from discord_onboarding.models import DiscordAuthRequest

        try:
            auth_request = DiscordAuthRequest.objects.create(
                discord_user_id=discord_user_id,
                guild_id=guild_id,
                requested_by_admin=admin_user,
            )
            return auth_request
        except Exception as e:
            logger.error(f"Error creating auth request: {e}")
            return None

    @commands.slash_command(
        name="auth",
        description=(
            "Get an authentication link to link your Discord account " "with EVE Online"
        ),
    )
    async def auth_command(self, ctx, user: discord.Member = None):
        """
        Generate authentication link for Discord to EVE Online linking
        """
        try:
            # Determine target user
            if user is None:
                # Self-authentication
                target_user = ctx.author
                is_admin_request = False
            else:
                # Admin targeting another user
                if not self._is_admin_user(ctx.author, ctx.guild):
                    embed = discord.Embed(
                        title="❌ Permission Denied",
                        description=(
                            "You don't have permission to generate authentication "
                            "links for other users."
                        ),
                        color=discord.Color.red(),
                    )
                    return await ctx.respond(embed=embed, ephemeral=True)

                target_user = user
                is_admin_request = True

            # Check rate limiting for target user
            if not self._check_rate_limit(target_user.id):
                embed = discord.Embed(
                    title="⏰ Rate Limited",
                    description=(
                        "Too many authentication requests today. "
                        "Please try again later."
                    ),
                    color=discord.Color.orange(),
                )
                return await ctx.respond(embed=embed, ephemeral=True)

            # Check if user is already authenticated
            from allianceauth.services.modules.discord.models import DiscordUser

            try:
                existing_discord_user = DiscordUser.objects.get(uid=target_user.id)
                if existing_discord_user.user:
                    user_desc = (
                        "You are"
                        if not is_admin_request
                        else f"{target_user.mention} is"
                    )
                    embed = discord.Embed(
                        title="✅ Already Authenticated",
                        description=f"{user_desc} already linked to Alliance Auth.",
                        color=discord.Color.green(),
                    )
                    embed.add_field(
                        name="Linked Account",
                        value=existing_discord_user.user.username,
                        inline=False,
                    )
                    return await ctx.respond(embed=embed, ephemeral=True)
            except DiscordUser.DoesNotExist:
                pass  # User not authenticated, continue

            # Create authentication request
            admin_user = None
            if is_admin_request:
                try:

                    admin_discord_user = DiscordUser.objects.get(uid=ctx.author.id)
                    admin_user = admin_discord_user.user
                except DiscordUser.DoesNotExist:
                    pass  # Admin not linked, but still allow the request

            auth_request = self._create_auth_request(
                discord_user_id=target_user.id,
                guild_id=ctx.guild.id if ctx.guild else None,
                admin_user=admin_user,
            )

            if not auth_request:
                embed = discord.Embed(
                    title="❌ Error",
                    description=(
                        "Failed to create authentication request. " "Please try again."
                    ),
                    color=discord.Color.red(),
                )
                return await ctx.respond(embed=embed, ephemeral=True)

            # Generate authentication URL
            auth_url = self._get_auth_url(auth_request.token)

            # Create embed
            embed = discord.Embed(
                title="🔗 EVE Online Authentication",
                description=(
                    "Click the link below to authenticate with EVE Online "
                    "and link your Discord account."
                ),
                color=discord.Color.blue(),
            )

            embed.add_field(
                name="Authentication Link",
                value=f"[Click here to authenticate]({auth_url})",
                inline=False,
            )

            embed.add_field(
                name="⏰ Expires",
                value=f"<t:{int(auth_request.expires_at.timestamp())}:R>",
                inline=True,
            )

            embed.add_field(
                name="🔒 Secure",
                value="This link is unique and expires in 24 hours",
                inline=True,
            )

            embed.set_footer(
                text=(
                    "After clicking the link, you'll be redirected to "
                    "EVE Online SSO for authentication."
                )
            )

            if is_admin_request:
                # Send to admin as ephemeral, then send DM to target user
                await ctx.respond(
                    f"Authentication link generated for {target_user.mention}",
                    ephemeral=True,
                )

                try:
                    await target_user.send(embed=embed)

                    # Send confirmation to admin
                    confirmation_embed = discord.Embed(
                        title="✅ Authentication Link Sent",
                        description=(
                            f"Authentication link has been sent to "
                            f"{target_user.mention} via DM."
                        ),
                        color=discord.Color.green(),
                    )
                    await ctx.followup.send(embed=confirmation_embed, ephemeral=True)

                except discord.Forbidden:
                    # Can't send DM, send link in channel
                    error_embed = discord.Embed(
                        title="⚠️ Cannot Send DM",
                        description=(
                            f"Could not send DM to {target_user.mention}. "
                            "Here's the authentication link:"
                        ),
                        color=discord.Color.orange(),
                    )
                    error_embed.add_field(
                        name="Authentication Link",
                        value=f"[Click here to authenticate]({auth_url})",
                        inline=False,
                    )
                    await ctx.followup.send(embed=error_embed, ephemeral=True)
            else:
                # Self-authentication - try to send DM first
                try:
                    await target_user.send(embed=embed)

                    confirmation_embed = discord.Embed(
                        title="📬 Check Your DMs",
                        description="An authentication link has been sent to your direct messages.",
                        color=discord.Color.green(),
                    )
                    await ctx.respond(embed=confirmation_embed, ephemeral=True)

                except discord.Forbidden:
                    # Can't send DM, send as ephemeral response
                    await ctx.respond(embed=embed, ephemeral=True)

            logger.info(
                f"Generated auth link for Discord user {target_user.id} ({target_user.name})"
            )

        except Exception as e:
            logger.error(f"Error in auth command: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="An unexpected error occurred. Please try again later.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """
        Send welcome message with authentication link when new member joins
        """
        try:
            from discord_onboarding.models import DiscordOnboardingConfiguration
            from discord_onboarding.tasks import send_welcome_auth_message

            config = DiscordOnboardingConfiguration.get_config()

            if not config.send_welcome_dm:
                return

            # Don't send to bots
            if member.bot:
                return

            # Check if user is already authenticated
            from allianceauth.services.modules.discord.models import DiscordUser

            try:
                existing_discord_user = DiscordUser.objects.get(uid=member.id)
                if existing_discord_user.user:
                    logger.info(
                        f"New member {member.name} is already authenticated, skipping welcome message"
                    )
                    return
            except DiscordUser.DoesNotExist:
                pass  # User not authenticated, send welcome message

            # Create authentication request
            auth_request = self._create_auth_request(
                discord_user_id=member.id, guild_id=member.guild.id
            )

            if not auth_request:
                logger.error(
                    f"Failed to create auth request for new member {member.name}"
                )
                return

            # Generate authentication URL
            auth_url = self._get_auth_url(auth_request.token)

            # Send welcome message via task (async)
            send_welcome_auth_message.delay(
                discord_user_id=member.id, guild_id=member.guild.id, auth_url=auth_url
            )

            logger.info(
                f"Sent welcome auth message to new member {member.name} ({member.id})"
            )

        except Exception as e:
            logger.error(
                f"Error sending welcome message to new member {member.name}: {e}"
            )

    @commands.slash_command(
        name="auth-status", description="Check authentication status"
    )
    @sender_has_perm("aadiscordbot.member_command_access")
    async def auth_status_command(self, ctx):
        """
        Check authentication status for the user
        """
        try:
            from allianceauth.services.modules.discord.models import DiscordUser

            from discord_onboarding.models import DiscordAuthRequest

            # Check if user is authenticated
            try:
                discord_user = DiscordUser.objects.get(uid=ctx.author.id)
                if discord_user.user:
                    embed = discord.Embed(
                        title="✅ Authenticated",
                        description="Your Discord account is linked to Alliance Auth.",
                        color=discord.Color.green(),
                    )
                    embed.add_field(
                        name="Linked Account",
                        value=discord_user.user.username,
                        inline=False,
                    )

                    # Get character information if available
                    try:
                        from allianceauth.authentication.models import (
                            CharacterOwnership,
                        )

                        main_character = CharacterOwnership.objects.filter(
                            user=discord_user.user
                        ).first()
                        if main_character:
                            embed.add_field(
                                name="Main Character",
                                value=f"{main_character.character.character_name} ({main_character.character.corporation_name})",
                                inline=False,
                            )
                    except Exception:
                        pass

                    return await ctx.respond(embed=embed, ephemeral=True)

            except DiscordUser.DoesNotExist:
                pass

            # User not authenticated - check for pending requests
            pending_requests = DiscordAuthRequest.objects.filter(
                discord_user_id=ctx.author.id,
                completed=False,
                expires_at__gt=timezone.now(),
            ).order_by("-created_at")

            if pending_requests.exists():
                latest_request = pending_requests.first()
                embed = discord.Embed(
                    title="⏳ Pending Authentication",
                    description="You have a pending authentication request.",
                    color=discord.Color.orange(),
                )
                embed.add_field(
                    name="Created",
                    value=f"<t:{int(latest_request.created_at.timestamp())}:R>",
                    inline=True,
                )
                embed.add_field(
                    name="Expires",
                    value=f"<t:{int(latest_request.expires_at.timestamp())}:R>",
                    inline=True,
                )
                embed.add_field(
                    name="Authentication Link",
                    value=f"[Click here to authenticate]({self._get_auth_url(latest_request.token)})",
                    inline=False,
                )
            else:
                embed = discord.Embed(
                    title="❌ Not Authenticated",
                    description="Your Discord account is not linked to Alliance Auth.",
                    color=discord.Color.red(),
                )
                embed.add_field(
                    name="Get Started",
                    value="Use the `/auth` command to generate an authentication link.",
                    inline=False,
                )

            await ctx.respond(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in auth-status command: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="An unexpected error occurred while checking authentication status.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(DiscordOnboardingCog(bot))
