# Generated Django migration for Discord Onboarding models

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("eveonline", "0017_alliance_and_corp_names_are_not_unique"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DiscordOnboardingConfiguration",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "send_welcome_dm",
                    models.BooleanField(
                        default=True, help_text="Send welcome DM to new Discord members"
                    ),
                ),
                (
                    "welcome_message_template",
                    models.TextField(
                        default="Welcome to our Discord server! 🎉\n\nTo complete your registration and get access to all channels, please authenticate with EVE Online by clicking the link below:\n\n{auth_link}\n\nThis link is valid for 24 hours. If you need a new link, use the `/auth` command in any channel.",
                        help_text="Template for welcome DM. Use {auth_link} placeholder for the authentication URL",
                    ),
                ),
                (
                    "auto_assign_authenticated_role",
                    models.BooleanField(
                        default=True,
                        help_text="Automatically assign authenticated role after successful EVE SSO",
                    ),
                ),
                (
                    "admin_role_ids",
                    models.TextField(
                        blank=True,
                        help_text="Comma-separated list of Discord role IDs that can use admin auth commands",
                    ),
                ),
                (
                    "max_requests_per_user_per_day",
                    models.IntegerField(
                        default=5,
                        help_text="Maximum auth requests per Discord user per day",
                    ),
                ),
            ],
            options={
                "verbose_name": "Discord Onboarding Configuration",
                "verbose_name_plural": "Discord Onboarding Configuration",
            },
        ),
        migrations.CreateModel(
            name="DiscordOnboardingStats",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("date", models.DateField(unique=True)),
                ("auth_requests_created", models.IntegerField(default=0)),
                ("auth_requests_completed", models.IntegerField(default=0)),
                ("auth_requests_expired", models.IntegerField(default=0)),
                ("new_discord_members", models.IntegerField(default=0)),
                ("successful_authentications", models.IntegerField(default=0)),
            ],
            options={
                "verbose_name": "Discord Onboarding Stats",
                "verbose_name_plural": "Discord Onboarding Stats",
                "ordering": ["-date"],
            },
        ),
        migrations.CreateModel(
            name="DiscordAuthRequest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("discord_user_id", models.BigIntegerField()),
                (
                    "token",
                    models.UUIDField(db_index=True, default=uuid.uuid4, unique=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("completed", models.BooleanField(default=False)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("guild_id", models.BigIntegerField(blank=True, null=True)),
                (
                    "auth_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="discord_auth_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "eve_character",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="eveonline.evecharacter",
                    ),
                ),
                (
                    "requested_by_admin",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="admin_discord_auth_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Discord Auth Request",
                "verbose_name_plural": "Discord Auth Requests",
            },
        ),
        migrations.AddIndex(
            model_name="discordauthrequest",
            index=models.Index(
                fields=["discord_user_id"], name="discord_onb_discord_c44b6a_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="discordauthrequest",
            index=models.Index(
                fields=["created_at"], name="discord_onb_created_91b8b7_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="discordauthrequest",
            index=models.Index(
                fields=["expires_at"], name="discord_onb_expires_57b827_idx"
            ),
        ),
    ]
