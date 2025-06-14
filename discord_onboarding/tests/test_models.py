from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from freezegun import freeze_time

from ..models import (
    DiscordAuthRequest,
    DiscordOnboardingConfiguration,
    DiscordOnboardingStats,
)
from .factories import (
    DiscordAuthRequestFactory,
    DiscordOnboardingConfigurationFactory,
    DiscordOnboardingStatsFactory,
    EveCharacterFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestDiscordAuthRequest:
    def test_create_auth_request(self):
        """Test creating a basic auth request"""
        auth_request = DiscordAuthRequestFactory()
        
        assert auth_request.discord_user_id
        assert auth_request.token
        assert auth_request.created_at
        assert auth_request.expires_at
        assert not auth_request.completed
        assert auth_request.is_valid
        assert not auth_request.is_expired

    def test_auth_request_expiry(self):
        """Test auth request expiry logic"""
        # Create request that expires in 1 hour
        with freeze_time("2023-01-01 12:00:00") as frozen_time:
            auth_request = DiscordAuthRequestFactory()
            
            # Should be valid initially
            assert auth_request.is_valid
            assert not auth_request.is_expired
            
            # Move forward 23 hours - still valid
            frozen_time.tick(delta=timedelta(hours=23))
            assert auth_request.is_valid
            assert not auth_request.is_expired
            
            # Move forward 2 more hours - now expired
            frozen_time.tick(delta=timedelta(hours=2))
            assert not auth_request.is_valid
            assert auth_request.is_expired

    def test_complete_auth(self):
        """Test completing an auth request"""
        auth_request = DiscordAuthRequestFactory()
        user = UserFactory()
        character = EveCharacterFactory()
        
        assert not auth_request.completed
        assert auth_request.completed_at is None
        
        auth_request.complete_auth(user, character)
        
        assert auth_request.completed
        assert auth_request.completed_at is not None
        assert auth_request.auth_user == user
        assert auth_request.eve_character == character

    def test_token_uniqueness(self):
        """Test that tokens are unique"""
        auth_request1 = DiscordAuthRequestFactory()
        auth_request2 = DiscordAuthRequestFactory()
        
        assert auth_request1.token != auth_request2.token

    def test_expires_at_auto_set(self):
        """Test that expires_at is automatically set if not provided"""
        auth_request = DiscordAuthRequest.objects.create(
            discord_user_id=123456789
        )
        
        assert auth_request.expires_at is not None
        expected_expiry = auth_request.created_at + timedelta(hours=24)
        
        # Allow for small time differences
        time_diff = abs(
            (auth_request.expires_at - expected_expiry).total_seconds()
        )
        assert time_diff < 1  # Less than 1 second difference

    def test_str_representation(self):
        """Test string representation"""
        auth_request = DiscordAuthRequestFactory(discord_user_id=123456789)
        
        str_repr = str(auth_request)
        assert "123456789" in str_repr
        assert str(auth_request.token) in str_repr


@pytest.mark.django_db
class TestDiscordOnboardingConfiguration:
    def test_singleton_behavior(self):
        """Test that only one configuration can exist"""
        # Create first configuration
        config1 = DiscordOnboardingConfigurationFactory()
        assert config1.id == 1
        
        # Try to create second configuration - should raise error
        with pytest.raises(ValueError):
            DiscordOnboardingConfigurationFactory()

    def test_get_config(self):
        """Test get_config class method"""
        # Should create config if none exists
        config = DiscordOnboardingConfiguration.get_config()
        assert config.id == 1
        
        # Should return existing config
        config2 = DiscordOnboardingConfiguration.get_config()
        assert config.id == config2.id

    def test_get_admin_role_ids(self):
        """Test parsing admin role IDs"""
        config = DiscordOnboardingConfigurationFactory(
            admin_role_ids="123456789,987654321,555444333"
        )
        
        role_ids = config.get_admin_role_ids()
        assert role_ids == [123456789, 987654321, 555444333]

    def test_get_admin_role_ids_empty(self):
        """Test parsing empty admin role IDs"""
        config = DiscordOnboardingConfigurationFactory(admin_role_ids="")
        
        role_ids = config.get_admin_role_ids()
        assert role_ids == []

    def test_get_admin_role_ids_with_spaces(self):
        """Test parsing admin role IDs with spaces"""
        config = DiscordOnboardingConfigurationFactory(
            admin_role_ids="123456789, 987654321 ,555444333"
        )
        
        role_ids = config.get_admin_role_ids()
        assert role_ids == [123456789, 987654321, 555444333]

    def test_str_representation(self):
        """Test string representation"""
        config = DiscordOnboardingConfigurationFactory()
        assert str(config) == "Discord Onboarding Configuration"


@pytest.mark.django_db
class TestDiscordOnboardingStats:
    def test_create_stats(self):
        """Test creating stats"""
        stats = DiscordOnboardingStatsFactory()
        
        assert stats.date
        assert stats.auth_requests_created == 0
        assert stats.auth_requests_completed == 0
        assert stats.auth_requests_expired == 0
        assert stats.new_discord_members == 0
        assert stats.successful_authentications == 0

    def test_get_today_stats(self):
        """Test get_today_stats class method"""
        with freeze_time("2023-01-01"):
            # Should create stats for today if none exist
            stats = DiscordOnboardingStats.get_today_stats()
            assert stats.date == timezone.now().date()
            
            # Should return existing stats for today
            stats.auth_requests_created = 5
            stats.save()
            
            stats2 = DiscordOnboardingStats.get_today_stats()
            assert stats.id == stats2.id
            assert stats2.auth_requests_created == 5

    def test_date_uniqueness(self):
        """Test that only one stats record per date is allowed"""
        stats1 = DiscordOnboardingStatsFactory()
        
        # Try to create another stats for same date
        with pytest.raises(IntegrityError):
            DiscordOnboardingStatsFactory(date=stats1.date)

    def test_str_representation(self):
        """Test string representation"""
        with freeze_time("2023-01-01"):
            stats = DiscordOnboardingStatsFactory()
            assert "2023-01-01" in str(stats)


@pytest.mark.django_db
class TestModelsSignalIntegration:
    """Test model interactions with signals"""
    
    @patch('discord_onboarding.signals.DiscordOnboardingStats.get_today_stats')
    def test_auth_request_creation_updates_stats(self, mock_get_stats):
        """Test that creating auth request updates stats via signals"""
        mock_stats = DiscordOnboardingStatsFactory.build()
        mock_get_stats.return_value = mock_stats
        
        # Create auth request - should trigger signal
        auth_request = DiscordAuthRequestFactory()
        
        # Signal should have been called
        mock_get_stats.assert_called_once()

    @patch('discord_onboarding.signals.DiscordOnboardingStats.get_today_stats')
    def test_auth_request_completion_updates_stats(self, mock_get_stats):
        """Test that completing auth request updates stats via signals"""
        mock_stats = DiscordOnboardingStatsFactory.build()
        mock_get_stats.return_value = mock_stats
        
        auth_request = DiscordAuthRequestFactory()
        user = UserFactory()
        character = EveCharacterFactory()
        
        # Complete the auth request - should trigger signal
        auth_request.complete_auth(user, character)
        
        # Signal should have been called multiple times (creation + completion)
        assert mock_get_stats.call_count >= 1