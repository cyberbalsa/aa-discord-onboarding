# AA Discord Onboarding

A Discord onboarding plugin for Alliance Auth that streamlines the process of linking Discord accounts with EVE Online characters.

## Features

- **Automatic Onboarding**: New Discord users receive a DM with an authentication link when they join the server
- **Simple Workflow**: One-click authentication via EVE SSO - no complex steps for users
- **Admin Commands**: Admins can send authentication links to specific users
- **Self-Service**: Users can generate new authentication links with `/auth`
- **Automatic Integration**: Seamlessly integrates with Alliance Auth's Discord service for role/nickname sync
- **Security**: Secure token-based authentication with automatic expiration

## Installation

1. Install the plugin:
```bash
pip install aa-discord-onboarding
```

2. Add the plugin to your Alliance Auth settings:
```python
INSTALLED_APPS = [
    # ... other apps
    'discord_onboarding',
    # ... other apps
]
```

3. Configure the plugin settings in your `local.py`:
```python
# Discord Onboarding Settings
DISCORD_ONBOARDING_BASE_URL = 'https://your-auth-site.com'  # Your Alliance Auth URL
DISCORD_ONBOARDING_TOKEN_EXPIRY = 3600  # Token expiry in seconds (default: 1 hour)
DISCORD_ONBOARDING_ADMIN_ROLES = [123456789, 987654321]  # Discord role IDs that can use admin commands
```

4. Run migrations:
```bash
python manage.py migrate discord_onboarding
```

5. Add the Discord cog to your Discord bot by adding it to your bot's installed cogs.

6. Add the URLs to your main `urls.py`:
```python
urlpatterns = [
    # ... existing patterns
    path('discord-onboarding/', include('discord_onboarding.urls')),
]
```

## Discord Bot Setup

The plugin includes a Discord cog that needs to be loaded by your Discord bot. If you're using the `aa-discordbot` package, the cog will be automatically discovered.

### Manual Cog Loading

If you need to manually load the cog:

```python
# In your bot setup
bot.load_extension('discord_onboarding.cogs.onboarding')
```

## Usage

### For End Users

1. **Automatic Onboarding**: When a user joins the Discord server, they automatically receive a DM with an authentication link
2. **Manual Authentication**: Users can use `/auth` in Discord to get a new authentication link
3. **Click & Authenticate**: Users click the link, authenticate with EVE Online, and their Discord account is automatically linked

### For Administrators

1. **Send Auth Links**: Use `/auth-user @username` to send an authentication link to a specific user
2. **Monitor Tokens**: View onboarding tokens and their status in the Django admin interface

### Workflow

1. User joins Discord server
2. Bot sends DM with unique authentication link
3. User clicks link → redirected to EVE SSO
4. User authenticates with EVE Online
5. Discord account automatically linked to Alliance Auth user
6. User receives appropriate Discord roles and nickname based on Alliance Auth permissions

## Commands

- `/auth` - Get a personal authentication link (ephemeral response)
- `/auth-user <member>` - Send an authentication link to another user (admin only)

## Permissions

The plugin creates the following permissions:
- `discord_onboarding.basic_access` - Can access Discord onboarding
- `discord_onboarding.admin_access` - Can send auth requests to other users

## Security Features

- **Token Expiration**: Authentication tokens expire after 1 hour (configurable)
- **Single Use**: Tokens can only be used once
- **Secure Generation**: Tokens use cryptographically secure random generation
- **Admin Validation**: Admin commands require proper role permissions
- **Session Protection**: Authentication state is protected in user sessions

## Troubleshooting

### Common Issues

1. **DMs Not Sending**: Ensure the bot has permission to send DMs and that users have DMs enabled
2. **Authentication Fails**: Check that EVE SSO is properly configured in Alliance Auth
3. **Role Sync Issues**: Verify that the Discord service is properly configured in Alliance Auth

### Logs

The plugin logs important events at the INFO level and errors at the ERROR level. Check your Alliance Auth logs for troubleshooting.

## Development

This plugin is designed to work with:
- Alliance Auth 3.0+
- aa-discordbot 2.0+
- Python 3.8+
- Django 4.0+

## License

This project is licensed under the MIT License.