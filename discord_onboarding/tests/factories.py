import uuid
from datetime import timedelta

import factory
from django.contrib.auth.models import User
from django.utils import timezone
from factory.django import DjangoModelFactory

from allianceauth.eveonline.models import EveCharacter
from allianceauth.services.modules.discord.models import DiscordUser

from ..models import (
    DiscordAuthRequest,
    DiscordOnboardingConfiguration,
    DiscordOnboardingStats,
)


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"testuser{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")


class EveCharacterFactory(DjangoModelFactory):
    class Meta:
        model = EveCharacter

    character_id = factory.Sequence(lambda n: 90000000 + n)
    character_name = factory.Faker("name")
    corporation_id = factory.Sequence(lambda n: 98000000 + n)
    corporation_name = factory.Faker("company")
    corporation_ticker = factory.LazyAttribute(
        lambda obj: obj.corporation_name[:5].upper()
    )
    alliance_id = factory.Sequence(lambda n: 99000000 + n)
    alliance_name = factory.Faker("company")
    alliance_ticker = factory.LazyAttribute(lambda obj: obj.alliance_name[:5].upper())


class DiscordUserFactory(DjangoModelFactory):
    class Meta:
        model = DiscordUser

    uid = factory.Sequence(lambda n: 100000000000000000 + n)
    user = factory.SubFactory(UserFactory)


class DiscordAuthRequestFactory(DjangoModelFactory):
    class Meta:
        model = DiscordAuthRequest

    discord_user_id = factory.Sequence(lambda n: 200000000000000000 + n)
    token = factory.LazyFunction(uuid.uuid4)
    created_at = factory.LazyFunction(timezone.now)
    expires_at = factory.LazyAttribute(
        lambda obj: obj.created_at + timedelta(hours=24)
    )
    completed = False
    guild_id = factory.Sequence(lambda n: 300000000000000000 + n)

    @factory.post_generation
    def completed_auth(self, create, extracted, **kwargs):
        if extracted:
            self.completed = True
            self.completed_at = timezone.now()
            self.auth_user = extracted.get("user")
            self.eve_character = extracted.get("character")
            if create:
                self.save()


class DiscordOnboardingConfigurationFactory(DjangoModelFactory):
    class Meta:
        model = DiscordOnboardingConfiguration

    id = 1
    send_welcome_dm = True
    welcome_message_template = (
        "Welcome! Please authenticate: {auth_link}"
    )
    auto_assign_authenticated_role = True
    admin_role_ids = "123456789,987654321"
    max_requests_per_user_per_day = 5


class DiscordOnboardingStatsFactory(DjangoModelFactory):
    class Meta:
        model = DiscordOnboardingStats

    date = factory.LazyFunction(lambda: timezone.now().date())
    auth_requests_created = 0
    auth_requests_completed = 0
    auth_requests_expired = 0
    new_discord_members = 0
    successful_authentications = 0