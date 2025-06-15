"""App settings for Discord Onboarding."""

from django.conf import settings

# Token expiration time in seconds (default: 1 hour)
DISCORD_ONBOARDING_TOKEN_EXPIRY = getattr(settings, 'DISCORD_ONBOARDING_TOKEN_EXPIRY', 3600)

# Base URL for the Alliance Auth installation
DISCORD_ONBOARDING_BASE_URL = getattr(settings, 'DISCORD_ONBOARDING_BASE_URL', 'https://auth.example.com')

# Discord bot admin roles (list of role IDs)
DISCORD_ONBOARDING_ADMIN_ROLES = getattr(settings, 'DISCORD_ONBOARDING_ADMIN_ROLES', [])

# Bypass email verification for Discord onboarding users
# When True, users who register through Discord onboarding will skip email verification
# and be automatically activated. This is useful when you want to streamline the onboarding
# process for Discord users. Note: This setting works independently of REGISTRATION_VERIFY_EMAIL
DISCORD_ONBOARDING_BYPASS_EMAIL_VERIFICATION = getattr(settings, 'DISCORD_ONBOARDING_BYPASS_EMAIL_VERIFICATION', False)
