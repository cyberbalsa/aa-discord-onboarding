# Auto-Kick Feature for Discord Onboarding

This feature automatically removes users from Discord servers who fail to authenticate within a configurable timeframe, with periodic reminder DMs.

## Features

- **Configurable Time Intervals**: Set custom reminder intervals (default 48 hours) and kick timeout (default 7 days)
- **Periodic Reminder DMs**: Sends fresh authentication links every 48 hours with countdown warnings
- **Auto-Kick After Timeout**: Automatically removes unauthenticated users with goodbye message
- **Channel Logging**: Logs kick events to a specified channel for admin visibility
- **Rate Limited**: Uses built-in Discord bot rate limiting system
- **Admin Interface**: Full Django admin interface for monitoring and manual control

## Configuration

Add these settings to your Alliance Auth `local.py`:

```python
# Enable auto-kick functionality
DISCORD_ONBOARDING_AUTO_KICK_ENABLED = True

# Time in hours after which to kick unauthenticated users (default: 7 days)
DISCORD_ONBOARDING_AUTO_KICK_TIMEOUT_HOURS = 168

# Interval in hours for sending reminder DMs (default: 48 hours)
DISCORD_ONBOARDING_REMINDER_INTERVAL_HOURS = 48

# Discord channel ID for logging kick notifications
DISCORD_ONBOARDING_KICK_LOG_CHANNEL_ID = 123456789012345678

# Enable/disable reminder DMs
DISCORD_ONBOARDING_REMINDERS_ENABLED = True

# Custom goodbye message for kicked users
DISCORD_ONBOARDING_KICK_GOODBYE_MESSAGE = "We're sorry to see you go! You were removed from the server because you didn't complete authentication within the required timeframe. If you'd like to rejoin in the future, please use the server invite link and complete the authentication process."
```

## How It Works

1. **User Joins Server**: When a user joins Discord, an `AutoKickSchedule` is created alongside the onboarding token
2. **Reminder Schedule**: Every 15 minutes, the system checks for users due for reminders (every 48 hours by default)
3. **Fresh Auth Links**: Each reminder includes a new authentication token that expires in 1 hour
4. **Auto-Kick**: After the timeout period (7 days by default), users are sent a goodbye DM and kicked from the server
5. **Authentication Cleanup**: When users successfully authenticate, their auto-kick schedule is deactivated
6. **Logging**: All kick events are logged to the specified channel with user details

## Database Schema

### AutoKickSchedule Model
- `discord_id`: Discord user ID (unique)
- `discord_username`: Discord username for reference
- `guild_id`: Discord guild ID where user joined
- `joined_at`: When the user joined the server
- `last_reminder_sent`: Last time a reminder was sent
- `kick_scheduled_at`: When the user should be kicked
- `is_active`: Whether the schedule is active
- `reminder_count`: Number of reminders sent

## Admin Features

The Django admin interface provides:
- **List View**: See all scheduled kicks with status indicators
- **Filtering**: Filter by active status, join date, reminder count
- **Actions**: Manually deactivate schedules or send immediate reminders
- **Status Display**: Visual indicators for due kicks, due reminders, inactive schedules
- **Time Calculations**: Shows time remaining until kick

## Task Schedule

- **Cleanup Task**: Runs daily at 2 AM to clean up expired tokens
- **Auto-Kick Processor**: Runs every 15 minutes to process reminders and kicks

## Integration

The system integrates seamlessly with:
- **Discord Bot Rate Limiting**: Uses the existing aadiscordbot rate limiting system
- **Alliance Auth SSO**: Deactivates schedules when users authenticate
- **Discord User Management**: Updates roles and nicknames after authentication
- **Logging System**: Uses Django logging for all events

## Security

- **Fresh Tokens**: Each reminder generates a new auth token
- **Permission Checks**: Bot verifies kick permissions before attempting
- **Error Handling**: Graceful handling of failed DMs and missing users
- **Audit Trail**: Complete logging of all auto-kick events

## Migration

Run the migration to create the AutoKickSchedule table:
```bash
python manage.py migrate discord_onboarding
```

## Monitoring

Monitor the feature through:
- Django admin interface at `/admin/discord_onboarding/autokickschedule/`
- Django logs for task execution
- Discord channel logs for kick events
- Celery task monitoring for reminder and kick queues