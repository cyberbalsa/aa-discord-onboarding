from django.conf import settings

# Discord Onboarding App Settings

# Default authentication link expiry time in hours
DISCORD_ONBOARDING_AUTH_EXPIRY_HOURS = getattr(
    settings, "DISCORD_ONBOARDING_AUTH_EXPIRY_HOURS", 24
)

# Maximum authentication requests per user per day
DISCORD_ONBOARDING_MAX_REQUESTS_PER_DAY = getattr(
    settings, "DISCORD_ONBOARDING_MAX_REQUESTS_PER_DAY", 5
)

# Whether to automatically send welcome DMs to new members
DISCORD_ONBOARDING_AUTO_WELCOME = getattr(
    settings, "DISCORD_ONBOARDING_AUTO_WELCOME", True
)

# Whether to automatically assign authenticated role after successful authentication
DISCORD_ONBOARDING_AUTO_ASSIGN_ROLE = getattr(
    settings, "DISCORD_ONBOARDING_AUTO_ASSIGN_ROLE", True
)

# Discord role IDs that can use admin commands (comma-separated string)
DISCORD_ONBOARDING_ADMIN_ROLES = getattr(settings, "DISCORD_ONBOARDING_ADMIN_ROLES", "")

# Custom welcome message template
DISCORD_ONBOARDING_WELCOME_MESSAGE = getattr(
    settings,
    "DISCORD_ONBOARDING_WELCOME_MESSAGE",
    (
        "Welcome to our Discord server! 🎉\n\n"
        "To complete your registration and get access to all channels, "
        "please authenticate with EVE Online by clicking the link below:\n\n"
        "{auth_link}\n\n"
        "This link is valid for 24 hours. If you need a new link, "
        "use the `/auth` command in any channel."
    ),
)
