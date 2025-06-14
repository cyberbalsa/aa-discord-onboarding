"""Admin interface for Discord Onboarding."""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import OnboardingToken


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
