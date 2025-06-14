"""Views for Discord Onboarding."""

import logging

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from allianceauth.services.modules.discord.models import DiscordUser

from .models import OnboardingToken

logger = logging.getLogger(__name__)


@login_required
@permission_required('discord_onboarding.basic_access', raise_exception=True)
def index(request):
    """Discord onboarding dashboard."""
    # Get recent tokens for display
    recent_tokens = OnboardingToken.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    context = {
        'recent_tokens': recent_tokens,
    }
    
    return render(request, 'discord_onboarding/index.html', context)


def onboarding_start(request, token):
    """Start the onboarding process with a token."""

    # Get the token from the database
    onboarding_token = get_object_or_404(OnboardingToken, token=token)

    # Check if token is valid
    if not onboarding_token.is_valid():
        return render(request, 'discord_onboarding/error.html', {
            'error_title': _('Invalid Token'),
            'error_message': _(
                'This onboarding link has expired or has already been used.'
            ),
        })

    # Redirect to ESI login with our callback
    from esi.clients import esi_client_factory

    # Build the callback URL
    callback_url = request.build_absolute_uri(reverse('discord_onboarding:callback'))

    # Create ESI client and get authorization URL
    client = esi_client_factory(callback_url=callback_url)
    auth_url = client.auth_uri(
        scopes=['esi-characters.read_contacts.v1'],  # Basic scope for character identification
        state=token  # Pass token as state parameter
    )

    return HttpResponseRedirect(auth_url)


def onboarding_callback(request):
    """Handle the callback after EVE SSO authentication."""

    # Get authorization code and state from the callback
    auth_code = request.GET.get('code')
    state = request.GET.get('state')

    if not auth_code or not state:
        return render(request, 'discord_onboarding/error.html', {
            'error_title': _('Authentication Error'),
            'error_message': _('Missing authentication parameters. Please try again.'),
        })

    try:
        onboarding_token = OnboardingToken.objects.get(token=state)
    except OnboardingToken.DoesNotExist:
        return render(request, 'discord_onboarding/error.html', {
            'error_title': _('Invalid Token'),
            'error_message': _('Invalid onboarding token.'),
        })

    # Check if token is still valid
    if not onboarding_token.is_valid():
        return render(request, 'discord_onboarding/error.html', {
            'error_title': _('Token Expired'),
            'error_message': _(
                'This onboarding link has expired or has already been used.'
            ),
        })

    try:
        from esi.clients import esi_client_factory
        from esi.models import Token
        from django.contrib.auth import authenticate, login

        # Build the callback URL
        callback_url = request.build_absolute_uri(reverse('discord_onboarding:callback'))

        # Create ESI client and exchange code for token
        client = esi_client_factory(callback_url=callback_url)
        esi_token = client.auth_code_to_token(auth_code)

        # Create or get the token object
        token = Token.objects.create(
            access_token=esi_token['access_token'],
            refresh_token=esi_token['refresh_token'],
            user=None,  # Will be set by authenticate
            character_id=esi_token['character_id'],
            character_name=esi_token['character_name'],
            character_owner_hash=esi_token['character_owner_hash'],
            token_type=esi_token['token_type'],
            expires_in=esi_token['expires_in']
        )

        # Authenticate user with the token
        user = authenticate(token=token)

        if not user:
            return render(request, 'discord_onboarding/error.html', {
                'error_title': _('Authentication Failed'),
                'error_message': _(
                    'Unable to authenticate with EVE Online. '
                    'Please ensure you are logging in with your main character.'
                ),
            })

        # Log the user in
        login(request, user)

        # Check if user already has a Discord account
        if DiscordUser.objects.filter(user=user).exists():
            # Update existing Discord user with new Discord ID
            discord_user = DiscordUser.objects.get(user=user)
            discord_user.uid = onboarding_token.discord_id
            discord_user.save()
            logger.info(
                f"Updated existing Discord user {user} "
                f"with new Discord ID {onboarding_token.discord_id}"
            )
        else:
            # Create new Discord user entry
            username_parts = onboarding_token.discord_username.split('#')
            username = username_parts[0] if '#' in onboarding_token.discord_username else onboarding_token.discord_username
            discriminator = username_parts[1] if '#' in onboarding_token.discord_username else ''

            DiscordUser.objects.create(
                user=user,
                uid=onboarding_token.discord_id,
                username=username,
                discriminator=discriminator,
            )
            logger.info(
                f"Created Discord user entry for {user} "
                f"with Discord ID {onboarding_token.discord_id}"
            )

        # Mark token as used
        onboarding_token.used = True
        onboarding_token.user = user
        onboarding_token.save()

        # Get main character name for display
        main_character = None
        if user.profile.main_character:
            main_character = user.profile.main_character.character_name

        return render(request, 'discord_onboarding/success.html', {
            'discord_username': onboarding_token.discord_username,
            'main_character': main_character,
            'user': user,
        })

    except Exception as e:
        logger.error(f"Error in onboarding callback: {e}")
        return render(request, 'discord_onboarding/error.html', {
            'error_title': _('Authentication Error'),
            'error_message': _('An error occurred during authentication. Please try again.'),
        })
