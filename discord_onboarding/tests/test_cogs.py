from unittest.mock import AsyncMock, Mock, patch

import discord
import pytest
from django.utils import timezone

from ..cogs.onboarding import DiscordOnboardingCog
from ..models import DiscordAuthRequest
from .factories import (
    DiscordAuthRequestFactory,
    DiscordOnboardingConfigurationFactory,
    DiscordUserFactory,
    UserFactory,
)


@pytest.mark.django_db
@pytest.mark.asyncio
class TestDiscordOnboardingCog:
    def setup_method(self):
        self.bot = Mock()
        self.cog = DiscordOnboardingCog(self.bot)
        
        # Mock Discord objects
        self.mock_guild = Mock(spec=discord.Guild)
        self.mock_guild.id = 123456789
        
        self.mock_user = Mock(spec=discord.Member)
        self.mock_user.id = 987654321
        self.mock_user.name = "TestUser"
        self.mock_user.mention = "<@987654321>"
        self.mock_user.bot = False
        
        self.mock_admin_user = Mock(spec=discord.Member)
        self.mock_admin_user.id = 111222333
        self.mock_admin_user.name = "AdminUser"
        
        self.mock_ctx = Mock()
        self.mock_ctx.guild = self.mock_guild
        self.mock_ctx.author = self.mock_user
        self.mock_ctx.respond = AsyncMock()
        self.mock_ctx.followup = Mock()
        self.mock_ctx.followup.send = AsyncMock()

    def test_get_auth_url(self):
        """Test auth URL generation"""
        token = "12345678-1234-1234-1234-123456789012"
        
        with patch('discord_onboarding.cogs.onboarding.get_site_url', return_value="https://example.com"):
            url = self.cog._get_auth_url(token)
        
        assert url == f"https://example.com/discord-onboarding/auth/{token}/"

    def test_is_admin_user_with_configured_roles(self):
        """Test admin user check with configured roles"""
        config = DiscordOnboardingConfigurationFactory(
            admin_role_ids="111111111,222222222"
        )
        
        # Mock user with admin role
        admin_role = Mock()
        admin_role.id = 111111111
        self.mock_admin_user.roles = [admin_role]
        
        self.mock_guild.get_member.return_value = self.mock_admin_user
        
        is_admin = self.cog._is_admin_user(self.mock_admin_user, self.mock_guild)
        assert is_admin is True

    def test_is_admin_user_without_admin_roles(self):
        """Test admin user check without admin roles"""
        config = DiscordOnboardingConfigurationFactory(
            admin_role_ids="111111111,222222222"
        )
        
        # Mock user without admin role
        regular_role = Mock()
        regular_role.id = 999999999
        self.mock_user.roles = [regular_role]
        
        self.mock_guild.get_member.return_value = self.mock_user
        
        is_admin = self.cog._is_admin_user(self.mock_user, self.mock_guild)
        assert is_admin is False

    def test_is_admin_user_with_administrator_permission(self):
        """Test admin user check with administrator permission"""
        config = DiscordOnboardingConfigurationFactory(admin_role_ids="")
        
        # Mock user with administrator permission
        self.mock_admin_user.guild_permissions.administrator = True
        self.mock_guild.get_member.return_value = self.mock_admin_user
        
        is_admin = self.cog._is_admin_user(self.mock_admin_user, self.mock_guild)
        assert is_admin is True

    def test_check_rate_limit_within_limit(self):
        """Test rate limit check within limit"""
        config = DiscordOnboardingConfigurationFactory(
            max_requests_per_user_per_day=5
        )
        
        # Create 3 requests for user (under limit)
        DiscordAuthRequestFactory.create_batch(3, discord_user_id=self.mock_user.id)
        
        within_limit = self.cog._check_rate_limit(self.mock_user.id)
        assert within_limit is True

    def test_check_rate_limit_exceeds_limit(self):
        """Test rate limit check exceeding limit"""
        config = DiscordOnboardingConfigurationFactory(
            max_requests_per_user_per_day=3
        )
        
        # Create 5 requests for user (over limit)
        DiscordAuthRequestFactory.create_batch(5, discord_user_id=self.mock_user.id)
        
        within_limit = self.cog._check_rate_limit(self.mock_user.id)
        assert within_limit is False

    def test_create_auth_request(self):
        """Test creating auth request"""
        request = self.cog._create_auth_request(
            discord_user_id=self.mock_user.id,
            guild_id=self.mock_guild.id
        )
        
        assert request is not None
        assert request.discord_user_id == self.mock_user.id
        assert request.guild_id == self.mock_guild.id
        assert request.token is not None

    async def test_auth_command_self_authentication(self):
        """Test /auth command for self-authentication"""
        config = DiscordOnboardingConfigurationFactory()
        
        self.mock_user.send = AsyncMock()
        
        await self.cog.auth_command(self.mock_ctx, user=None)
        
        # Should try to send DM to user
        self.mock_user.send.assert_called_once()
        
        # Should respond with confirmation
        self.mock_ctx.respond.assert_called_once()
        
        # Should create auth request
        auth_request = DiscordAuthRequest.objects.get(
            discord_user_id=self.mock_user.id
        )
        assert auth_request is not None

    async def test_auth_command_admin_targeting(self):
        """Test /auth command for admin targeting another user"""
        config = DiscordOnboardingConfigurationFactory(
            admin_role_ids="111111111"
        )
        
        # Mock admin user
        admin_role = Mock()
        admin_role.id = 111111111
        self.mock_ctx.author = self.mock_admin_user
        self.mock_admin_user.roles = [admin_role]
        self.mock_guild.get_member.return_value = self.mock_admin_user
        
        target_user = Mock(spec=discord.Member)
        target_user.id = 555666777
        target_user.mention = "<@555666777>"
        target_user.send = AsyncMock()
        
        await self.cog.auth_command(self.mock_ctx, user=target_user)
        
        # Should send DM to target user
        target_user.send.assert_called_once()
        
        # Should create auth request for target user
        auth_request = DiscordAuthRequest.objects.get(
            discord_user_id=target_user.id
        )
        assert auth_request is not None

    async def test_auth_command_non_admin_targeting(self):
        """Test /auth command non-admin trying to target another user"""
        config = DiscordOnboardingConfigurationFactory(
            admin_role_ids="111111111"
        )
        
        # Mock regular user (no admin role)
        regular_role = Mock()
        regular_role.id = 999999999
        self.mock_user.roles = [regular_role]
        self.mock_guild.get_member.return_value = self.mock_user
        
        target_user = Mock(spec=discord.Member)
        target_user.id = 555666777
        
        await self.cog.auth_command(self.mock_ctx, user=target_user)
        
        # Should respond with permission denied
        self.mock_ctx.respond.assert_called_once()
        call_args = self.mock_ctx.respond.call_args[1]
        assert "Permission Denied" in str(call_args["embed"].title)

    async def test_auth_command_already_authenticated_user(self):
        """Test /auth command for already authenticated user"""
        config = DiscordOnboardingConfigurationFactory()
        
        # Create existing Discord user
        discord_user = DiscordUserFactory(uid=self.mock_user.id)
        
        await self.cog.auth_command(self.mock_ctx, user=None)
        
        # Should respond with already authenticated message
        self.mock_ctx.respond.assert_called_once()
        call_args = self.mock_ctx.respond.call_args[1]
        assert "Already Authenticated" in str(call_args["embed"].title)

    async def test_auth_command_rate_limited(self):
        """Test /auth command when rate limited"""
        config = DiscordOnboardingConfigurationFactory(
            max_requests_per_user_per_day=1
        )
        
        # Create existing request to trigger rate limit
        DiscordAuthRequestFactory(discord_user_id=self.mock_user.id)
        
        await self.cog.auth_command(self.mock_ctx, user=None)
        
        # Should respond with rate limit message
        self.mock_ctx.respond.assert_called_once()
        call_args = self.mock_ctx.respond.call_args[1]
        assert "Rate Limited" in str(call_args["embed"].title)

    async def test_auth_command_dm_forbidden(self):
        """Test /auth command when DM is forbidden"""
        config = DiscordOnboardingConfigurationFactory()
        
        # Mock DM send failure
        self.mock_user.send = AsyncMock(side_effect=discord.Forbidden(Mock(), "Cannot send messages"))
        
        await self.cog.auth_command(self.mock_ctx, user=None)
        
        # Should still respond (with link as ephemeral)
        self.mock_ctx.respond.assert_called_once()

    async def test_on_member_join_sends_welcome(self):
        """Test on_member_join sends welcome message"""
        config = DiscordOnboardingConfigurationFactory(send_welcome_dm=True)
        
        with patch('discord_onboarding.cogs.onboarding.send_welcome_auth_message.delay') as mock_task:
            await self.cog.on_member_join(self.mock_user)
            
            mock_task.assert_called_once()
            call_args = mock_task.call_args[1]
            assert call_args["discord_user_id"] == self.mock_user.id
            assert call_args["guild_id"] == self.mock_user.guild.id
            assert "auth_url" in call_args

    async def test_on_member_join_disabled_welcome(self):
        """Test on_member_join when welcome is disabled"""
        config = DiscordOnboardingConfigurationFactory(send_welcome_dm=False)
        
        with patch('discord_onboarding.cogs.onboarding.send_welcome_auth_message.delay') as mock_task:
            await self.cog.on_member_join(self.mock_user)
            
            mock_task.assert_not_called()

    async def test_on_member_join_bot_user(self):
        """Test on_member_join ignores bot users"""
        config = DiscordOnboardingConfigurationFactory(send_welcome_dm=True)
        
        bot_user = Mock(spec=discord.Member)
        bot_user.bot = True
        
        with patch('discord_onboarding.cogs.onboarding.send_welcome_auth_message.delay') as mock_task:
            await self.cog.on_member_join(bot_user)
            
            mock_task.assert_not_called()

    async def test_on_member_join_already_authenticated(self):
        """Test on_member_join with already authenticated user"""
        config = DiscordOnboardingConfigurationFactory(send_welcome_dm=True)
        
        # Create existing Discord user
        discord_user = DiscordUserFactory(uid=self.mock_user.id)
        
        with patch('discord_onboarding.cogs.onboarding.send_welcome_auth_message.delay') as mock_task:
            await self.cog.on_member_join(self.mock_user)
            
            mock_task.assert_not_called()

    async def test_auth_status_command_authenticated(self):
        """Test /auth-status command for authenticated user"""
        discord_user = DiscordUserFactory(uid=self.mock_user.id)
        
        await self.cog.auth_status_command(self.mock_ctx)
        
        self.mock_ctx.respond.assert_called_once()
        call_args = self.mock_ctx.respond.call_args[1]
        assert "Authenticated" in str(call_args["embed"].title)

    async def test_auth_status_command_pending(self):
        """Test /auth-status command with pending request"""
        auth_request = DiscordAuthRequestFactory(
            discord_user_id=self.mock_user.id,
            completed=False
        )
        
        await self.cog.auth_status_command(self.mock_ctx)
        
        self.mock_ctx.respond.assert_called_once()
        call_args = self.mock_ctx.respond.call_args[1]
        assert "Pending Authentication" in str(call_args["embed"].title)

    async def test_auth_status_command_not_authenticated(self):
        """Test /auth-status command for non-authenticated user"""
        await self.cog.auth_status_command(self.mock_ctx)
        
        self.mock_ctx.respond.assert_called_once()
        call_args = self.mock_ctx.respond.call_args[1]
        assert "Not Authenticated" in str(call_args["embed"].title)


@pytest.mark.django_db
@pytest.mark.asyncio
class TestDiscordOnboardingCogIntegration:
    """Integration tests for the Discord cog"""
    
    def setup_method(self):
        self.bot = Mock()
        self.cog = DiscordOnboardingCog(self.bot)
        
        self.mock_guild = Mock(spec=discord.Guild)
        self.mock_guild.id = 123456789
        
        self.mock_user = Mock(spec=discord.Member)
        self.mock_user.id = 987654321
        self.mock_user.name = "TestUser"
        self.mock_user.mention = "<@987654321>"
        self.mock_user.bot = False
        self.mock_user.guild = self.mock_guild
        
        self.mock_ctx = Mock()
        self.mock_ctx.guild = self.mock_guild
        self.mock_ctx.author = self.mock_user
        self.mock_ctx.respond = AsyncMock()

    async def test_complete_onboarding_flow(self):
        """Test complete onboarding flow simulation"""
        config = DiscordOnboardingConfigurationFactory(send_welcome_dm=True)
        
        # Step 1: User joins server
        with patch('discord_onboarding.cogs.onboarding.send_welcome_auth_message.delay') as mock_welcome:
            await self.cog.on_member_join(self.mock_user)
            
            # Should create auth request and send welcome
            mock_welcome.assert_called_once()
            auth_request = DiscordAuthRequest.objects.get(
                discord_user_id=self.mock_user.id
            )
            assert auth_request is not None
            assert not auth_request.completed
        
        # Step 2: User manually requests auth (should show existing request)
        await self.cog.auth_status_command(self.mock_ctx)
        
        call_args = self.mock_ctx.respond.call_args[1]
        assert "Pending Authentication" in str(call_args["embed"].title)
        
        # Step 3: Simulate auth completion
        user = UserFactory()
        from .factories import EveCharacterFactory
        character = EveCharacterFactory()
        
        auth_request.complete_auth(user, character)
        
        # Step 4: Check status again - should show authenticated
        await self.cog.auth_status_command(self.mock_ctx)
        
        # Get the latest call
        latest_call_args = self.mock_ctx.respond.call_args[1]
        assert "Authenticated" in str(latest_call_args["embed"].title)

    async def test_admin_workflow(self):
        """Test admin workflow for generating auth links"""
        config = DiscordOnboardingConfigurationFactory(
            admin_role_ids="111111111"
        )
        
        # Setup admin user
        admin_user = Mock(spec=discord.Member)
        admin_user.id = 111111111
        admin_user.name = "AdminUser"
        
        admin_role = Mock()
        admin_role.id = 111111111
        admin_user.roles = [admin_role]
        
        self.mock_guild.get_member.return_value = admin_user
        self.mock_ctx.author = admin_user
        
        # Setup target user
        target_user = Mock(spec=discord.Member)
        target_user.id = 555666777
        target_user.mention = "<@555666777>"
        target_user.send = AsyncMock()
        
        # Admin generates auth link for target user
        await self.cog.auth_command(self.mock_ctx, user=target_user)
        
        # Should create auth request for target user
        auth_request = DiscordAuthRequest.objects.get(
            discord_user_id=target_user.id
        )
        assert auth_request is not None
        assert auth_request.requested_by_admin is None  # No AllianceAuth user linked
        
        # Should send DM to target user
        target_user.send.assert_called_once()
        
        # Should respond to admin
        self.mock_ctx.respond.assert_called_once()