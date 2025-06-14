from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from django.utils import timezone
from freezegun import freeze_time

from ..models import DiscordAuthRequest, DiscordOnboardingStats
from ..tasks import (
    cleanup_expired_auth_requests,
    send_auth_success_notification,
    send_welcome_auth_message,
    update_character_information,
)
from .factories import (
    DiscordAuthRequestFactory,
    DiscordOnboardingConfigurationFactory,
    DiscordOnboardingStatsFactory,
    EveCharacterFactory,
)


@pytest.mark.django_db
class TestSendAuthSuccessNotification:
    @patch('discord_onboarding.tasks.send_direct_message.delay')
    def test_send_auth_success_notification(self, mock_send_dm):
        """Test sending authentication success notification"""
        discord_user_id = 123456789
        character_name = "Test Character"
        guild_id = 987654321
        
        send_auth_success_notification(discord_user_id, character_name, guild_id)
        
        mock_send_dm.assert_called_once()
        call_args = mock_send_dm.call_args
        
        assert call_args[1]["user_id"] == discord_user_id
        assert character_name in call_args[1]["message"]
        assert "Authentication Successful" in call_args[1]["message"]

    @patch('discord_onboarding.tasks.send_direct_message.delay')
    def test_send_auth_success_notification_exception_handling(self, mock_send_dm):
        """Test exception handling in success notification"""
        mock_send_dm.side_effect = Exception("Test error")
        
        # Should not raise exception
        send_auth_success_notification(123456789, "Test Character")


@pytest.mark.django_db
class TestSendWelcomeAuthMessage:
    @patch('discord_onboarding.tasks.send_direct_message.delay')
    def test_send_welcome_auth_message(self, mock_send_dm):
        """Test sending welcome authentication message"""
        config = DiscordOnboardingConfigurationFactory()
        discord_user_id = 123456789
        guild_id = 987654321
        auth_url = "https://example.com/auth/token123"
        
        send_welcome_auth_message(discord_user_id, guild_id, auth_url)
        
        mock_send_dm.assert_called_once()
        call_args = mock_send_dm.call_args
        
        assert call_args[1]["user_id"] == discord_user_id
        assert auth_url in call_args[1]["message"]

    @patch('discord_onboarding.tasks.send_direct_message.delay')
    def test_send_welcome_auth_message_disabled(self, mock_send_dm):
        """Test welcome message when disabled in config"""
        config = DiscordOnboardingConfigurationFactory(send_welcome_dm=False)
        
        send_welcome_auth_message(123456789, 987654321, "https://example.com/auth")
        
        mock_send_dm.assert_not_called()

    @patch('discord_onboarding.tasks.send_direct_message.delay')
    def test_send_welcome_auth_message_updates_stats(self, mock_send_dm):
        """Test that welcome message updates member stats"""
        config = DiscordOnboardingConfigurationFactory()
        stats = DiscordOnboardingStatsFactory()
        initial_members = stats.new_discord_members
        
        send_welcome_auth_message(123456789, 987654321, "https://example.com/auth")
        
        stats.refresh_from_db()
        assert stats.new_discord_members == initial_members + 1

    @patch('discord_onboarding.tasks.send_direct_message.delay')
    def test_send_welcome_auth_message_exception_handling(self, mock_send_dm):
        """Test exception handling in welcome message"""
        mock_send_dm.side_effect = Exception("Test error")
        
        # Should not raise exception
        send_welcome_auth_message(123456789, 987654321, "https://example.com/auth")


@pytest.mark.django_db
class TestCleanupExpiredAuthRequests:
    def test_cleanup_expired_auth_requests(self):
        """Test cleanup of expired auth requests"""
        with freeze_time("2023-01-01 12:00:00") as frozen_time:
            # Create requests at different times
            # Old expired request (should be deleted)
            old_expired = DiscordAuthRequestFactory()
            
            # Move forward 8 days
            frozen_time.tick(delta=timedelta(days=8))
            
            # Recent expired request (should be kept)
            recent_expired = DiscordAuthRequestFactory()
            
            # Move forward 1 day (now 9 days from old_expired)
            frozen_time.tick(delta=timedelta(days=1))
            
            # Valid request (should be kept)
            valid_request = DiscordAuthRequestFactory()
            
            # All requests should exist initially
            assert DiscordAuthRequest.objects.count() == 3
            
            # Run cleanup
            cleanup_expired_auth_requests()
            
            # Only old expired request should be deleted
            remaining_requests = DiscordAuthRequest.objects.all()
            assert remaining_requests.count() == 2
            assert old_expired.id not in [r.id for r in remaining_requests]
            assert recent_expired.id in [r.id for r in remaining_requests]
            assert valid_request.id in [r.id for r in remaining_requests]

    def test_cleanup_updates_stats(self):
        """Test that cleanup updates expiry stats"""
        with freeze_time("2023-01-01 12:00:00"):
            # Create expired request for today
            expired_today = DiscordAuthRequestFactory()
            
        with freeze_time("2023-01-01 13:00:00"):
            stats = DiscordOnboardingStatsFactory()
            initial_expired = stats.auth_requests_expired
            
            cleanup_expired_auth_requests()
            
            stats.refresh_from_db()
            assert stats.auth_requests_expired == initial_expired + 1

    def test_cleanup_exception_handling(self):
        """Test exception handling in cleanup task"""
        with patch('discord_onboarding.tasks.DiscordAuthRequest.objects.filter') as mock_filter:
            mock_filter.side_effect = Exception("Database error")
            
            # Should not raise exception
            cleanup_expired_auth_requests()


@pytest.mark.django_db
class TestUpdateCharacterInformation:
    def test_update_character_information(self):
        """Test updating character information"""
        character = EveCharacterFactory()
        
        with patch.object(character, 'update_character') as mock_update:
            update_character_information(character.character_id)
            mock_update.assert_called_once()

    def test_update_character_information_not_found(self):
        """Test updating non-existent character"""
        # Should not raise exception for non-existent character
        update_character_information(999999999)

    def test_update_character_information_exception_handling(self):
        """Test exception handling in character update"""
        character = EveCharacterFactory()
        
        with patch.object(character, 'update_character') as mock_update:
            mock_update.side_effect = Exception("ESI error")
            
            # Should not raise exception
            update_character_information(character.character_id)


@pytest.mark.django_db
class TestTasksIntegration:
    """Integration tests for task workflows"""
    
    @patch('discord_onboarding.tasks.send_direct_message.delay')
    def test_complete_onboarding_workflow(self, mock_send_dm):
        """Test complete onboarding workflow using tasks"""
        config = DiscordOnboardingConfigurationFactory()
        stats = DiscordOnboardingStatsFactory()
        
        discord_user_id = 123456789
        guild_id = 987654321
        auth_url = "https://example.com/auth/token123"
        character_name = "Test Character"
        
        initial_members = stats.new_discord_members
        
        # Step 1: Send welcome message (when user joins)
        send_welcome_auth_message(discord_user_id, guild_id, auth_url)
        
        # Check welcome message was sent
        assert mock_send_dm.call_count == 1
        welcome_call = mock_send_dm.call_args_list[0]
        assert welcome_call[1]["user_id"] == discord_user_id
        assert auth_url in welcome_call[1]["message"]
        
        # Check stats updated
        stats.refresh_from_db()
        assert stats.new_discord_members == initial_members + 1
        
        # Step 2: Send success notification (when auth completes)
        send_auth_success_notification(discord_user_id, character_name, guild_id)
        
        # Check success message was sent
        assert mock_send_dm.call_count == 2
        success_call = mock_send_dm.call_args_list[1]
        assert success_call[1]["user_id"] == discord_user_id
        assert character_name in success_call[1]["message"]
        assert "Authentication Successful" in success_call[1]["message"]

    def test_periodic_cleanup_workflow(self):
        """Test periodic cleanup workflow"""
        with freeze_time("2023-01-01 12:00:00") as frozen_time:
            # Create various auth requests
            completed_request = DiscordAuthRequestFactory()
            completed_request.completed = True
            completed_request.save()
            
            valid_request = DiscordAuthRequestFactory()
            
            # Old expired request
            old_expired = DiscordAuthRequestFactory()
            
            # Move time forward
            frozen_time.tick(delta=timedelta(days=8))
            
            # Recent expired request
            recent_expired = DiscordAuthRequestFactory()
            
            assert DiscordAuthRequest.objects.count() == 4
            
            # Run cleanup
            cleanup_expired_auth_requests()
            
            # Should only remove old expired incomplete request
            remaining = DiscordAuthRequest.objects.all()
            remaining_ids = [r.id for r in remaining]
            
            assert completed_request.id in remaining_ids  # Completed, keep
            assert valid_request.id in remaining_ids      # Valid, keep
            assert recent_expired.id in remaining_ids     # Recent, keep
            assert old_expired.id not in remaining_ids    # Old expired, remove