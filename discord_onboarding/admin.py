from django.contrib import admin
from django.utils.html import format_html

from .models import (
    DiscordAuthRequest,
    DiscordOnboardingConfiguration,
    DiscordOnboardingStats,
)


@admin.register(DiscordAuthRequest)
class DiscordAuthRequestAdmin(admin.ModelAdmin):
    list_display = [
        "discord_user_id",
        "token_short",
        "status",
        "created_at",
        "expires_at",
        "auth_user",
        "eve_character",
    ]
    list_filter = ["completed", "created_at", "expires_at", "requested_by_admin"]
    search_fields = [
        "discord_user_id",
        "token",
        "auth_user__username",
        "eve_character__character_name",
    ]
    readonly_fields = ["token", "created_at", "completed_at", "is_expired", "is_valid"]

    def token_short(self, obj):
        return str(obj.token)[:8] + "..."

    token_short.short_description = "Token"

    def status(self, obj):
        if obj.completed:
            return format_html('<span style="color: green;">✓ Completed</span>')
        elif obj.is_expired:
            return format_html('<span style="color: red;">✗ Expired</span>')
        else:
            return format_html('<span style="color: orange;">⏳ Pending</span>')

    status.short_description = "Status"


@admin.register(DiscordOnboardingConfiguration)
class DiscordOnboardingConfigurationAdmin(admin.ModelAdmin):
    fieldsets = [
        (
            "Welcome Message Settings",
            {"fields": ("send_welcome_dm", "welcome_message_template")},
        ),
        ("Role Assignment", {"fields": ("auto_assign_authenticated_role",)}),
        ("Admin Settings", {"fields": ("admin_role_ids",)}),
        ("Rate Limiting", {"fields": ("max_requests_per_user_per_day",)}),
    ]

    def has_add_permission(self, request):
        # Only allow one configuration
        return not DiscordOnboardingConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of the configuration
        return False


@admin.register(DiscordOnboardingStats)
class DiscordOnboardingStatsAdmin(admin.ModelAdmin):
    list_display = [
        "date",
        "new_discord_members",
        "auth_requests_created",
        "auth_requests_completed",
        "successful_authentications",
        "completion_rate",
    ]
    list_filter = ["date"]
    readonly_fields = list_display

    def completion_rate(self, obj):
        if obj.auth_requests_created == 0:
            return "0%"
        rate = (obj.auth_requests_completed / obj.auth_requests_created) * 100
        return f"{rate:.1f}%"

    completion_rate.short_description = "Completion Rate"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
