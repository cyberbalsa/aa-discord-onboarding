# Discord Onboarding Plugin for Alliance Auth

A comprehensive Discord onboarding plugin that seamlessly integrates EVE Online authentication with Discord, providing a frictionless user experience for new members.

## Features

- **One-Click Authentication**: Users get a unique authentication link via DM when they join Discord
- **EVE SSO Integration**: Seamless EVE Online Single Sign-On authentication
- **Admin Tools**: Admins can generate auth links for specific users with `/auth @user`
- **Rate Limiting**: Configurable rate limits to prevent abuse
- **Auto-Role Assignment**: Automatic role assignment after successful authentication
- **Statistics Tracking**: Comprehensive analytics on authentication success rates
- **Secure Tokens**: Time-limited, unique authentication tokens (24-hour expiry)

## Workflow

1. **User joins Discord** → Bot automatically detects new member
2. **Bot sends DM** → Unique authentication link sent to user's DMs
3. **User clicks link** → Redirected to EVE Online SSO authentication
4. **EVE SSO callback** → Discord ID automatically linked to EVE character
5. **User authenticated** → Roles assigned, access granted, success notification sent

## Installation

### Via pip (Recommended)

```bash
pip install aa-discord-onboarding
```

### From source

```bash
git clone https://github.com/jetbalsa/aa-discord-onboarding.git
cd aa-discord-onboarding
pip install .
```

### Configuration

#### 1. Add to INSTALLED_APPS

Add the plugin to your Alliance Auth `local.py`:

```python
INSTALLED_APPS = [
    # ... other apps
    'discord_onboarding',
    # ... other apps
]
```

#### 2. Run Migrations

```bash
python manage.py migrate discord_onboarding
```

#### 3. Configure Settings (Optional)

Add these optional settings to your `local.py`:

```python
# Discord Onboarding Settings
DISCORD_ONBOARDING_AUTH_EXPIRY_HOURS = 24  # How long auth links are valid
DISCORD_ONBOARDING_MAX_REQUESTS_PER_DAY = 5  # Rate limiting per user
DISCORD_ONBOARDING_AUTO_WELCOME = True  # Send welcome DM to new members
DISCORD_ONBOARDING_AUTO_ASSIGN_ROLE = True  # Auto-assign authenticated role
DISCORD_ONBOARDING_ADMIN_ROLES = '123456789,987654321'  # Admin role IDs (comma-separated)

# Custom welcome message template
DISCORD_ONBOARDING_WELCOME_MESSAGE = '''
Welcome to our Alliance Discord! 🚀

To get full access to all channels and features, please authenticate with EVE Online:

{auth_link}

This secure link expires in 24 hours. If you need help, contact an admin!
'''
```

#### 4. Update URL Configuration

Add to your main `urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # ... other URLs
    path('discord-onboarding/', include('discord_onboarding.urls')),
    # ... other URLs
]
```

#### 5. Restart Services

Restart your Alliance Auth and Discord bot services:

```bash
# Restart Alliance Auth
systemctl restart allianceauth

# Restart Discord Bot
systemctl restart allianceauth-discordbot
```

## Configuration

### Admin Panel

Access the Django admin panel to configure:

1. **Discord Onboarding Configuration**
   - Enable/disable welcome DMs
   - Customize welcome message template
   - Set admin role IDs
   - Configure rate limiting

2. **Monitor Statistics**
   - View daily authentication stats
   - Track success/failure rates
   - Monitor new member onboarding

### Discord Permissions

Ensure the bot has these permissions:
- Send Messages (for DMs)
- Read Message History
- Use Slash Commands
- Manage Roles (for auto-assignment)

## Usage

### User Commands

#### `/auth`
- **Description**: Generate authentication link for yourself
- **Usage**: `/auth`
- **Response**: Bot sends authentication link via DM

#### `/auth @user` (Admin Only)
- **Description**: Generate authentication link for another user
- **Usage**: `/auth @username`
- **Permissions**: Requires admin role or Administrator permission
- **Response**: Bot sends authentication link to target user's DM

#### `/auth-status`
- **Description**: Check your authentication status
- **Usage**: `/auth-status`
- **Response**: Shows current authentication status and character info

### Automatic Features

- **New Member Welcome**: Automatically sends welcome DM with auth link
- **Rate Limiting**: Prevents spam (5 requests per user per day by default)
- **Token Security**: Unique, time-limited tokens for each request
- **Character Updates**: Automatically updates EVE character information

## Authentication Flow Details

### 1. Token Generation
```
Discord User → Bot creates unique UUID token → Stored in database with expiry
```

### 2. EVE SSO Authentication
```
User clicks link → Alliance Auth EVE SSO → EVE Online authentication → Callback
```

### 3. Account Linking
```
EVE character verified → User account created/linked → Discord ID associated → Roles assigned
```

### 4. Success Notification
```
Authentication complete → Discord notification sent → User gets full access
```

## Security Features

- **Unique Tokens**: Each authentication request uses a unique UUID
- **Time Limits**: Tokens expire after 24 hours (configurable)
- **Rate Limiting**: Prevents abuse with configurable daily limits
- **Admin Controls**: Restricted admin commands with role-based permissions
- **Secure Sessions**: Django session management for authentication flow

## Troubleshooting

### Bot Not Responding to Commands
- Check bot permissions in Discord server
- Verify bot is online and connected
- Check Discord bot logs for errors

### Authentication Link Not Working
- Ensure Alliance Auth is properly configured for EVE SSO
- Check that URLs are accessible from outside your network
- Verify SSL certificates are valid

### Users Not Getting DMs
- Check bot can send DMs (user hasn't blocked bot)
- Verify bot has "Send Messages" permission
- Check Discord privacy settings

### Database Issues
- Run migrations: `python manage.py migrate discord_onboarding`
- Check database connectivity
- Verify user permissions

## API Endpoints

- `GET /discord-onboarding/auth/<token>/` - Start authentication
- `GET /discord-onboarding/callback/<token>/` - EVE SSO callback
- `GET /discord-onboarding/status/<token>/` - Check auth status (JSON)

## Monitoring

### Admin Panel Statistics
- Daily authentication requests
- Success/failure rates
- New member counts
- Rate limiting statistics

### Logs
Monitor these log files:
- Alliance Auth: Authentication flow logs
- Discord Bot: Command execution logs
- Celery: Background task logs

## Support

- **Documentation**: Check Alliance Auth documentation
- **Issues**: Report bugs to your Alliance Auth administrator
- **Discord**: Use `/auth-status` to check authentication state
- **Logs**: Check server logs for detailed error information

## License

This plugin is part of the Alliance Auth ecosystem and follows the same licensing terms.