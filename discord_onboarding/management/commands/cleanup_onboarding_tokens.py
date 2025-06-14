"""Management command to clean up expired onboarding tokens."""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from discord_onboarding.models import OnboardingToken


class Command(BaseCommand):
    help = 'Clean up expired onboarding tokens'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Delete tokens older than this many days (default: 1)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']

        cutoff_date = timezone.now() - timedelta(days=days)

        tokens_to_delete = OnboardingToken.objects.filter(
            created_at__lt=cutoff_date
        )

        count = tokens_to_delete.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {count} onboarding tokens older than {days} days'
                )
            )
            for token in tokens_to_delete[:10]:  # Show first 10
                self.stdout.write(f'  - {token}')
            if count > 10:
                self.stdout.write(f'  ... and {count - 10} more')
        else:
            tokens_to_delete.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {count} onboarding tokens older than {days} days'
                )
            )
