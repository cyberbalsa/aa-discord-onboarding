"""Admin interface for Discord Onboarding."""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import OnboardingToken, AutoKickSchedule


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
    actions = ['deactivate_schedules', 'send_reminder_now']

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

    def has_add_permission(self, request):
        # Schedules should be created by the bot, not manually
        return False
