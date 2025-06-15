"""Admin interface for Discord Onboarding."""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import OnboardingToken, AutoKickSchedule
from allianceauth.services.modules.discord.models import DiscordUser
from .app_settings import DISCORD_ONBOARDING_AUTO_KICK_ENABLED


@admin.register(OnboardingToken)
class OnboardingTokenAdmin(admin.ModelAdmin):
    list_display = (
        'discord_username',
        'discord_id',
        'user',
        'status_display',
        'created_at',
        'expires_at'
    )
    list_filter = ('used', 'created_at', 'expires_at')
    search_fields = ('discord_username', 'discord_id', 'user__username', 'token')
    readonly_fields = ('token', 'created_at', 'expires_at', 'status_display')
    ordering = ('-created_at',)

    def status_display(self, obj):
        if obj.used:
            return format_html(
                '<span style="color: green;"><i class="fas fa-check"></i> {}</span>',
                _('Used')
            )
        elif obj.is_expired():
            return format_html(
                '<span style="color: red;"><i class="fas fa-times"></i> {}</span>',
                _('Expired')
            )
        else:
            return format_html(
                '<span style="color: orange;"><i class="fas fa-clock"></i> {}</span>',
                _('Pending')
            )

    status_display.short_description = _('Status')

    def has_add_permission(self, request):
        # Tokens should be created by the bot, not manually
        return False


@admin.register(AutoKickSchedule)
class AutoKickScheduleAdmin(admin.ModelAdmin):
    list_display = (
        'discord_username',
        'discord_id',
        'guild_id',
        'status_display',
        'joined_at',
        'kick_scheduled_at',
        'reminder_count',
        'last_reminder_sent'
    )
    list_filter = ('is_active', 'joined_at', 'kick_scheduled_at', 'reminder_count')
    search_fields = ('discord_username', 'discord_id', 'guild_id')
    readonly_fields = ('joined_at', 'status_display', 'time_until_kick')
    ordering = ('-joined_at',)
    actions = ['deactivate_schedules', 'send_reminder_now', 'add_all_orphaned_users', 'clear_all_schedules']

    def status_display(self, obj):
        if not obj.is_active:
            return format_html(
                '<span style="color: gray;"><i class="fas fa-pause"></i> {}</span>',
                _('Inactive')
            )
        elif obj.is_due_for_kick():
            return format_html(
                '<span style="color: red;"><i class="fas fa-exclamation-triangle"></i> {}</span>',
                _('Due for Kick')
            )
        elif obj.is_due_for_reminder():
            return format_html(
                '<span style="color: orange;"><i class="fas fa-bell"></i> {}</span>',
                _('Due for Reminder')
            )
        else:
            return format_html(
                '<span style="color: blue;"><i class="fas fa-clock"></i> {}</span>',
                _('Scheduled')
            )

    status_display.short_description = _('Status')

    def time_until_kick(self, obj):
        if not obj.is_active:
            return _('N/A - Inactive')
        
        from django.utils import timezone
        time_left = obj.kick_scheduled_at - timezone.now()
        
        if time_left.total_seconds() <= 0:
            return _('Overdue')
        
        days = time_left.days
        hours, remainder = divmod(time_left.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    time_until_kick.short_description = _('Time Until Kick')

    def deactivate_schedules(self, request, queryset):
        """Deactivate selected auto-kick schedules."""
        count = 0
        for schedule in queryset:
            if schedule.is_active:
                schedule.deactivate()
                count += 1
        
        self.message_user(request, _(f'Deactivated {count} auto-kick schedules.'))

    deactivate_schedules.short_description = _('Deactivate selected schedules')

    def send_reminder_now(self, request, queryset):
        """Send reminder DM to selected users immediately."""
        from .tasks import send_onboarding_reminder
        
        count = 0
        for schedule in queryset.filter(is_active=True):
            send_onboarding_reminder.delay(schedule.id)
            count += 1
        
        self.message_user(request, _(f'Queued {count} reminder messages.'))

    send_reminder_now.short_description = _('Send reminder now')

    def add_all_orphaned_users(self, request, queryset):
        """Add all unlinked Discord users from all servers to auto-kick timeline."""
        
        if not DISCORD_ONBOARDING_AUTO_KICK_ENABLED:
            self.message_user(request, _('Auto-kick feature is not enabled.'), level='ERROR')
            return

        try:
            # We need to get Discord server information, but this admin action doesn't have guild context
            # So we'll work with existing schedules to determine which guilds we should process
            existing_guilds = set(AutoKickSchedule.objects.values_list('guild_id', flat=True).distinct())
            
            if not existing_guilds:
                self.message_user(request, _(
                    'No existing auto-kick schedules found to determine Discord servers. '
                    'Please use the Discord slash command /onboarding-admin add_orphans_to_autokick '
                    'from within the Discord server instead.'
                ), level='WARNING')
                return

            # Since we can't access Discord bot context from Django admin,
            # we'll create a task to handle this via the Discord bot
            from .tasks import add_orphaned_users_admin_task
            
            # Create a custom task to handle this
            try:
                # Schedule the task with the guild IDs we found
                guild_list = list(existing_guilds)
                add_orphaned_users_admin_task.delay(guild_list)
                
                self.message_user(request, _(
                    f'Queued task to add orphaned users from {len(guild_list)} Discord servers. '
                    f'Check the logs for results. Note: This requires the Discord bot to be online.'
                ))
            except Exception as e:
                self.message_user(request, _(
                    f'Unable to queue task: {e}. '
                    f'Please use the Discord slash command /onboarding-admin add_orphans_to_autokick instead.'
                ), level='ERROR')

        except Exception as e:
            self.message_user(request, _(f'Error: {e}'), level='ERROR')

    add_all_orphaned_users.short_description = _('Add all orphaned Discord users to auto-kick timeline')

    def clear_all_schedules(self, request, queryset):
        """Clear all active auto-kick schedules (deactivate them all)."""
        
        try:
            # Get all active schedules, not just the queryset
            all_active_schedules = AutoKickSchedule.objects.filter(is_active=True)
            total_count = all_active_schedules.count()

            if total_count == 0:
                self.message_user(request, _('No active auto-kick schedules found to clear.'))
                return

            # Deactivate all active schedules
            deactivated_count = 0
            failed_count = 0
            
            for schedule in all_active_schedules:
                try:
                    schedule.deactivate()
                    deactivated_count += 1
                except Exception as e:
                    failed_count += 1
                    # Log the error but continue processing
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to deactivate schedule for {schedule.discord_username}: {e}")

            # Report results
            if failed_count == 0:
                self.message_user(request, _(
                    f'Successfully cleared {deactivated_count} auto-kick schedules. '
                    f'Users will no longer receive reminder DMs or be auto-kicked.'
                ))
            else:
                self.message_user(request, _(
                    f'Cleared {deactivated_count} schedules successfully, but {failed_count} failed. '
                    f'Check the logs for details.'
                ), level='WARNING')

        except Exception as e:
            self.message_user(request, _(f'Error clearing schedules: {e}'), level='ERROR')

    clear_all_schedules.short_description = _('Clear all auto-kick schedules (deactivate all)')

    def has_add_permission(self, request):
        # Schedules should be created by the bot, not manually
        return False
