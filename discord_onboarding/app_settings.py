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

# Auto-kick settings
# Enable/disable auto-kick functionality
DISCORD_ONBOARDING_AUTO_KICK_ENABLED = getattr(settings, 'DISCORD_ONBOARDING_AUTO_KICK_ENABLED', False)

# Time in hours after which to kick unauthenticated users (default: 7 days)
DISCORD_ONBOARDING_AUTO_KICK_TIMEOUT_HOURS = getattr(settings, 'DISCORD_ONBOARDING_AUTO_KICK_TIMEOUT_HOURS', 168)

# Interval in hours for sending reminder DMs (default: 48 hours)
DISCORD_ONBOARDING_REMINDER_INTERVAL_HOURS = getattr(settings, 'DISCORD_ONBOARDING_REMINDER_INTERVAL_HOURS', 48)

# Discord channel ID for logging kick notifications
DISCORD_ONBOARDING_KICK_LOG_CHANNEL_ID = getattr(settings, 'DISCORD_ONBOARDING_KICK_LOG_CHANNEL_ID', None)

# Custom goodbye message for kicked users
DISCORD_ONBOARDING_KICK_GOODBYE_MESSAGE = getattr(settings, 'DISCORD_ONBOARDING_KICK_GOODBYE_MESSAGE', 
    "We're sorry to see you go! You were removed from the server because you didn't complete authentication within the required timeframe. "
    "If you'd like to rejoin in the future, please use the server invite link and complete the authentication process.")

# Enable/disable reminder DMs
DISCORD_ONBOARDING_REMINDERS_ENABLED = getattr(settings, 'DISCORD_ONBOARDING_REMINDERS_ENABLED', True)
