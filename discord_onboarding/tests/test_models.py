"""Tests for Discord Onboarding models."""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from ..models import OnboardingToken


class OnboardingTokenTestCase(TestCase):
    """Test cases for OnboardingToken model."""

    def test_token_generation(self):
        """Test that tokens are automatically generated."""
        token = OnboardingToken.objects.create(
            discord_id=123456789,
            discord_username="testuser#1234"
        )

        self.assertIsNotNone(token.token)
        self.assertEqual(len(token.token), 64)
        self.assertIsNotNone(token.expires_at)

    def test_token_expiry(self):
        """Test token expiry functionality."""
        # Create expired token
        token = OnboardingToken.objects.create(
            discord_id=123456789,
            discord_username="testuser#1234"
        )

        # Manually set expiry to past
        token.expires_at = timezone.now() - timedelta(hours=1)
        token.save()

        self.assertTrue(token.is_expired())
        self.assertFalse(token.is_valid())

    def test_token_usage(self):
        """Test token usage functionality."""
        token = OnboardingToken.objects.create(
            discord_id=123456789,
            discord_username="testuser#1234"
        )

        # Token should be valid initially
        self.assertTrue(token.is_valid())

        # Mark as used
        token.used = True
        token.save()

        # Should no longer be valid
        self.assertFalse(token.is_valid())

    def test_string_representation(self):
        """Test string representation of token."""
        token = OnboardingToken.objects.create(
            discord_id=123456789,
            discord_username="testuser#1234"
        )

        str_repr = str(token)
        self.assertIn("testuser#1234", str_repr)
        self.assertIn("valid", str_repr)
