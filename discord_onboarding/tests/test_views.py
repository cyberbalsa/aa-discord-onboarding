import json
from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import reverse
from freezegun import freeze_time

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.services.modules.discord.models import DiscordUser

from ..models import DiscordAuthRequest
from ..views import auth_callback, auth_start, auth_status, index
from .factories import (
    DiscordAuthRequestFactory,
    DiscordOnboardingStatsFactory,
    DiscordUserFactory,
    EveCharacterFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestIndexView:
    def setup_method(self):
        self.factory = RequestFactory()
        self.user = UserFactory()

    def test_index_view_authenticated_user(self):
        """Test index view for authenticated user"""
        request = self.factory.get("/")
        request.user = self.user
        
        response = index(request)
        
        assert response.status_code == 200
        assert "recent_stats" in response.context_data
        assert "user_discord_linked" in response.context_data
        assert "recent_requests" in response.context_data

    def test_index_view_with_discord_user(self):
        """Test index view for user with Discord linked"""
        discord_user = DiscordUserFactory(user=self.user)
        request = self.factory.get("/")
        request.user = self.user
        
        response = index(request)
        
        assert response.status_code == 200
        assert response.context_data["user_discord_linked"] is True
        assert response.context_data["user_discord_id"] == discord_user.uid

    def test_index_view_without_discord_user(self):
        """Test index view for user without Discord linked"""
        request = self.factory.get("/")
        request.user = self.user
        
        response = index(request)
        
        assert response.status_code == 200
        assert response.context_data["user_discord_linked"] is False
        assert response.context_data["user_discord_id"] is None

    def test_index_view_with_stats_and_requests(self):
        """Test index view with existing stats and requests"""
        # Create some stats and requests
        DiscordOnboardingStatsFactory.create_batch(3)
        DiscordAuthRequestFactory.create_batch(5)
        
        request = self.factory.get("/")
        request.user = self.user
        
        response = index(request)
        
        assert response.status_code == 200
        assert len(response.context_data["recent_stats"]) <= 7
        assert len(response.context_data["recent_requests"]) <= 10


@pytest.mark.django_db
class TestAuthStartView:
    def setup_method(self):
        self.factory = RequestFactory()

    def test_auth_start_valid_token(self):
        """Test auth start view with valid token"""
        auth_request = DiscordAuthRequestFactory()
        
        response = auth_start(self.factory.get("/"), auth_request.token)
        
        assert response.status_code == 302
        assert "authentication:login" in response.url

    def test_auth_start_invalid_token(self):
        """Test auth start view with invalid token"""
        import uuid
        invalid_token = uuid.uuid4()
        
        response = auth_start(self.factory.get("/"), invalid_token)
        
        assert response.status_code == 200
        assert "Invalid Authentication Link" in response.content.decode()

    def test_auth_start_expired_token(self):
        """Test auth start view with expired token"""
        with freeze_time("2023-01-01 12:00:00"):
            auth_request = DiscordAuthRequestFactory()
        
        # Token is now expired
        response = auth_start(self.factory.get("/"), auth_request.token)
        
        assert response.status_code == 200
        assert "Authentication Link Expired" in response.content.decode()

    def test_auth_start_sets_session(self):
        """Test that auth start sets session token"""
        auth_request = DiscordAuthRequestFactory()
        request = self.factory.get("/")
        request.session = {}
        
        response = auth_start(request, auth_request.token)
        
        assert request.session["discord_auth_token"] == str(auth_request.token)


@pytest.mark.django_db
class TestAuthCallbackView:
    def setup_method(self):
        self.factory = RequestFactory()
        self.user = UserFactory()
        self.character = EveCharacterFactory()

    def test_auth_callback_no_session_token(self):
        """Test auth callback without session token"""
        request = self.factory.get("/")
        request.session = {}
        request.user = self.user
        
        response = auth_callback(request, "dummy-token")
        
        assert response.status_code == 200
        assert "Authentication Error" in response.content.decode()

    def test_auth_callback_invalid_session_token(self):
        """Test auth callback with invalid session token"""
        import uuid
        request = self.factory.get("/")
        request.session = {"discord_auth_token": str(uuid.uuid4())}
        request.user = self.user
        
        response = auth_callback(request, "dummy-token")
        
        assert response.status_code == 200
        assert "Authentication Error" in response.content.decode()

    def test_auth_callback_expired_request(self):
        """Test auth callback with expired auth request"""
        with freeze_time("2023-01-01 12:00:00"):
            auth_request = DiscordAuthRequestFactory()
        
        request = self.factory.get("/")
        request.session = {"discord_auth_token": str(auth_request.token)}
        request.user = self.user
        
        response = auth_callback(request, "dummy-token")
        
        assert response.status_code == 200
        assert "Authentication Expired" in response.content.decode()

    def test_auth_callback_unauthenticated_user(self):
        """Test auth callback with unauthenticated user"""
        auth_request = DiscordAuthRequestFactory()
        request = self.factory.get("/")
        request.session = {"discord_auth_token": str(auth_request.token)}
        request.user = AnonymousUser()
        
        response = auth_callback(request, "dummy-token")
        
        assert response.status_code == 200
        assert "Authentication Required" in response.content.decode()

    def test_auth_callback_no_character_ownership(self):
        """Test auth callback with user who has no character ownership"""
        auth_request = DiscordAuthRequestFactory()
        request = self.factory.get("/")
        request.session = {"discord_auth_token": str(auth_request.token)}
        request.user = self.user
        
        response = auth_callback(request, "dummy-token")
        
        assert response.status_code == 200
        assert "No Character Found" in response.content.decode()

    @patch('discord_onboarding.views.send_auth_success_notification.delay')
    def test_auth_callback_successful(self, mock_notification):
        """Test successful auth callback"""
        auth_request = DiscordAuthRequestFactory()
        
        # Create character ownership
        CharacterOwnership.objects.create(
            user=self.user,
            character=self.character,
            owner_hash="test-hash"
        )
        
        request = self.factory.get("/")
        request.session = {"discord_auth_token": str(auth_request.token)}
        request.user = self.user
        
        response = auth_callback(request, "dummy-token")
        
        assert response.status_code == 200
        assert "Authentication Successful" in response.content.decode()
        assert self.character.character_name in response.content.decode()
        
        # Check that Discord user was created/linked
        discord_user = DiscordUser.objects.get(uid=auth_request.discord_user_id)
        assert discord_user.user == self.user
        
        # Check that auth request was completed
        auth_request.refresh_from_db()
        assert auth_request.completed
        assert auth_request.auth_user == self.user
        assert auth_request.eve_character == self.character
        
        # Check that notification task was called
        mock_notification.assert_called_once_with(
            discord_user_id=auth_request.discord_user_id,
            character_name=self.character.character_name,
            guild_id=auth_request.guild_id
        )

    def test_auth_callback_update_existing_discord_user(self):
        """Test auth callback updates existing Discord user"""
        auth_request = DiscordAuthRequestFactory()
        other_user = UserFactory()
        
        # Create existing Discord user linked to different user
        DiscordUser.objects.create(
            uid=auth_request.discord_user_id,
            user=other_user
        )
        
        # Create character ownership
        CharacterOwnership.objects.create(
            user=self.user,
            character=self.character,
            owner_hash="test-hash"
        )
        
        request = self.factory.get("/")
        request.session = {"discord_auth_token": str(auth_request.token)}
        request.user = self.user
        
        response = auth_callback(request, "dummy-token")
        
        assert response.status_code == 200
        
        # Check that Discord user was updated
        discord_user = DiscordUser.objects.get(uid=auth_request.discord_user_id)
        assert discord_user.user == self.user  # Should be updated to new user


@pytest.mark.django_db
class TestAuthStatusView:
    def setup_method(self):
        self.factory = RequestFactory()

    def test_auth_status_valid_token(self):
        """Test auth status with valid token"""
        auth_request = DiscordAuthRequestFactory()
        
        response = auth_status(self.factory.get("/"), auth_request.token)
        
        assert response.status_code == 200
        
        data = json.loads(response.content)
        assert data["completed"] is False
        assert data["expired"] is False
        assert data["valid"] is True
        assert "created_at" in data
        assert "expires_at" in data

    def test_auth_status_invalid_token(self):
        """Test auth status with invalid token"""
        import uuid
        invalid_token = uuid.uuid4()
        
        response = auth_status(self.factory.get("/"), invalid_token)
        
        assert response.status_code == 400

    def test_auth_status_completed_request(self):
        """Test auth status with completed request"""
        user = UserFactory()
        character = EveCharacterFactory()
        auth_request = DiscordAuthRequestFactory()
        auth_request.complete_auth(user, character)
        
        response = auth_status(self.factory.get("/"), auth_request.token)
        
        assert response.status_code == 200
        
        data = json.loads(response.content)
        assert data["completed"] is True
        assert data["character_name"] == character.character_name

    def test_auth_status_expired_request(self):
        """Test auth status with expired request"""
        with freeze_time("2023-01-01 12:00:00"):
            auth_request = DiscordAuthRequestFactory()
        
        response = auth_status(self.factory.get("/"), auth_request.token)
        
        assert response.status_code == 200
        
        data = json.loads(response.content)
        assert data["completed"] is False
        assert data["expired"] is True
        assert data["valid"] is False


@pytest.mark.django_db
class TestViewsIntegration:
    """Integration tests for the complete auth flow"""
    
    def test_complete_auth_flow(self):
        """Test complete authentication flow from start to finish"""
        factory = RequestFactory()
        user = UserFactory()
        character = EveCharacterFactory()
        
        # Step 1: Create auth request
        auth_request = DiscordAuthRequestFactory()
        
        # Step 2: Start auth process
        start_request = factory.get("/")
        start_request.session = {}
        
        start_response = auth_start(start_request, auth_request.token)
        assert start_response.status_code == 302
        assert start_request.session["discord_auth_token"] == str(auth_request.token)
        
        # Step 3: Complete auth process
        CharacterOwnership.objects.create(
            user=user,
            character=character,
            owner_hash="test-hash"
        )
        
        callback_request = factory.get("/")
        callback_request.session = start_request.session
        callback_request.user = user
        
        with patch('discord_onboarding.views.send_auth_success_notification.delay'):
            callback_response = auth_callback(callback_request, "dummy-token")
        
        assert callback_response.status_code == 200
        assert "Authentication Successful" in callback_response.content.decode()
        
        # Step 4: Check final status
        status_response = auth_status(factory.get("/"), auth_request.token)
        data = json.loads(status_response.content)
        
        assert data["completed"] is True
        assert data["character_name"] == character.character_name
        
        # Verify Discord user was created
        discord_user = DiscordUser.objects.get(uid=auth_request.discord_user_id)
        assert discord_user.user == user