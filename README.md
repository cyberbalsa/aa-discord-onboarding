# AA Discord Onboarding

A Discord onboarding plugin for Alliance Auth that streamlines the process of linking Discord accounts with EVE Online characters.

## Features

- **Automatic Onboarding**: New Discord users receive a DM with an authentication link when they join the server
- **Simple Workflow**: One-click authentication via EVE SSO - no complex steps for users
- **Admin Commands**: Admins can send authentication links to specific users
- **Self-Service**: Users can generate new authentication links with `/bind`
- **Automatic Integration**: Seamlessly integrates with Alliance Auth's Discord service for role/nickname sync
- **Security**: Secure token-based authentication with automatic expiration

## Installation

### Production Installation (from PyPI)

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

### Development Installation (from Git)

If you want to hack on the code or install the latest development version:

1. **Clone the repository:**
```bash
cd /path/to/your/allianceauth/
git clone https://github.com/cyberbalsa/aa-discord-onboarding.git
```

2. **Install in development mode:**
```bash
# Activate your Alliance Auth virtual environment first
source venv/bin/activate  # or however you activate your venv

# Install in editable/development mode
pip install -e aa-discord-onboarding/
```

3. **Configure Alliance Auth** (same as production):
```python
# In your local.py or settings file
INSTALLED_APPS = [
    # ... other apps
    'discord_onboarding',
    # ... other apps
]

# Discord Onboarding Settings
DISCORD_ONBOARDING_BASE_URL = 'https://your-auth-site.com'
DISCORD_ONBOARDING_TOKEN_EXPIRY = 3600  # 1 hour
DISCORD_ONBOARDING_ADMIN_ROLES = [123456789, 987654321]  # Discord role IDs
```

4. **Run migrations:**
```bash
python manage.py migrate discord_onboarding
```

5. **Load the Discord cog** (add to your Discord bot configuration)

6. **Restart services:**
```bash
# Restart Alliance Auth
sudo systemctl restart allianceauth-gunicorn
sudo systemctl restart allianceauth-worker

# Restart Discord bot (however you run it)
sudo systemctl restart your-discord-bot
```

### Development Workflow

When developing:

1. **Make your changes** to the code in `aa-discord-onboarding/discord_onboarding/`

2. **Test your changes:**
```bash
# Run tests
cd aa-discord-onboarding/
python -m pytest

# Run linting
python -m flake8 discord_onboarding/ --max-line-length=120 --exclude=migrations

# Test package building
python -m build
```

3. **Restart services** to see changes (Django will auto-reload in development mode)

4. **Database changes** require new migrations:
```bash
python manage.py makemigrations discord_onboarding
python manage.py migrate discord_onboarding
```

### Development Tips

- **Log files**: Check Alliance Auth logs for debugging: `tail -f /var/log/allianceauth/allianceauth.log`
- **Discord bot logs**: Check your Discord bot logs for cog-related issues
- **Database**: Use Django admin at `/admin/` to view OnboardingToken objects
- **Testing tokens**: Use the cleanup command to clear test tokens: `python manage.py cleanup_onboarding_tokens --dry-run`

## Discord Bot Setup

The plugin includes a Discord cog that needs to be loaded by your Discord bot. If you're using the `aa-discordbot` package, the cog will be automatically discovered.

### Manual Cog Loading

If you need to manually load the cog:

```python
# In your bot setup
bot.load_extension('discord_onboarding.cogs.onboarding')
```

### Development Cog Loading

For development installations, you may need to ensure the cog is discoverable:

1. **If using aa-discordbot**: The cog should be automatically discovered if the package is installed in the same environment.

2. **Manual loading in development**:
```python
# If you're running the Discord bot separately, add the path
import sys
sys.path.append('/path/to/your/aa-discord-onboarding')

# Then load the cog
bot.load_extension('discord_onboarding.cogs.onboarding')
```

3. **For Docker setups**: Mount the development directory:
```yaml
# In docker-compose.yml
volumes:
  - /path/to/aa-discord-onboarding:/app/aa-discord-onboarding
```

## Usage

### For End Users

1. **Automatic Onboarding**: When a user joins the Discord server, they automatically receive a DM with an authentication link
2. **Manual Authentication**: Users can use `/bind` in Discord to get a new authentication link
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

- `/bind` - Get a personal authentication link (ephemeral response)
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

### Development Troubleshooting

**Common development issues:**

1. **Cog not loading**: 
   - Check Discord bot logs for import errors
   - Ensure `discord_onboarding` is in Python path
   - Verify the package is installed with `pip list | grep discord-onboarding`

2. **Database errors**:
   - Run migrations: `python manage.py migrate discord_onboarding`
   - Check if app is in `INSTALLED_APPS`

3. **Import errors**:
   - Install in development mode: `pip install -e aa-discord-onboarding/`
   - Check virtual environment is activated

4. **Template not found**:
   - Restart Alliance Auth services after installing
   - Check `TEMPLATES` setting includes `APP_DIRS = True`

5. **ESI/SSO issues**:
   - Verify ESI settings in Alliance Auth
   - Check callback URL configuration
   - Ensure `DISCORD_ONBOARDING_BASE_URL` matches your domain

## Development

This plugin is designed to work with:
- Alliance Auth 3.0+
- aa-discordbot 2.0+
- Python 3.8+
- Django 4.0+

## License

This project is licensed under the MIT License.