# Generated migration for AutoKickSchedule model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('discord_onboarding', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AutoKickSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('discord_id', models.BigIntegerField(help_text='Discord user ID', unique=True)),
                ('discord_username', models.CharField(help_text='Discord username for reference', max_length=100)),
                ('guild_id', models.BigIntegerField(help_text='Discord guild ID where user joined')),
                ('joined_at', models.DateTimeField(help_text='When the user joined the server')),
                ('last_reminder_sent', models.DateTimeField(blank=True, help_text='Last time a reminder was sent', null=True)),
                ('kick_scheduled_at', models.DateTimeField(help_text='When the user should be kicked')),
                ('is_active', models.BooleanField(default=True, help_text='Whether the schedule is active')),
                ('reminder_count', models.IntegerField(default=0, help_text='Number of reminders sent')),
            ],
            options={
                'verbose_name': 'Auto-Kick Schedule',
                'verbose_name_plural': 'Auto-Kick Schedules',
            },
        ),
        migrations.AddIndex(
            model_name='autokickschedule',
            index=models.Index(fields=['kick_scheduled_at', 'is_active'], name='discord_onb_kick_sc_74c7ea_idx'),
        ),
        migrations.AddIndex(
            model_name='autokickschedule',
            index=models.Index(fields=['last_reminder_sent', 'is_active'], name='discord_onb_last_re_4b5c9a_idx'),
        ),
    ]