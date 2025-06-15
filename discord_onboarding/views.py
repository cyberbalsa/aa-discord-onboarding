"""Views for Discord Onboarding."""

import logging

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.contrib.auth import authenticate, login

from allianceauth.services.modules.discord.models import DiscordUser

from .models import OnboardingToken, AutoKickSchedule
from .app_settings import (
    DISCORD_ONBOARDING_BYPASS_EMAIL_VERIFICATION,
    DISCORD_ONBOARDING_KICK_LOG_CHANNEL_ID
)

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

    # Store the onboarding token in session for the callback
    request.session['onboarding_token'] = token
    
    # Set session flag to bypass email verification if configured
    if DISCORD_ONBOARDING_BYPASS_EMAIL_VERIFICATION:
        request.session['discord_onboarding_bypass_email'] = True
        
        # Set a simple cache flag for our signal handler to detect
        from django.core.cache import cache
        cache.set('discord_onboarding_active', True, timeout=600)  # 10 minute timeout
        logger.debug("Set Discord onboarding cache flag: discord_onboarding_active")

    # Redirect to our custom SSO login that handles email bypass
    next_url = reverse('discord_onboarding:callback')
    if DISCORD_ONBOARDING_BYPASS_EMAIL_VERIFICATION:
        sso_login_url = reverse('discord_onboarding:sso_login')
    else:
        sso_login_url = reverse('auth_sso_login')
    return HttpResponseRedirect(f"{sso_login_url}?next={next_url}")


@login_required
def onboarding_callback(request):
    """Handle the callback after Alliance Auth SSO authentication."""

    # Get the onboarding token from session
    token = request.session.get('onboarding_token')
    
    if not token:
        return render(request, 'discord_onboarding/error.html', {
            'error_title': _('Invalid Session'),
            'error_message': _('No onboarding token found in session. Please try again.'),
        })

    try:
        onboarding_token = OnboardingToken.objects.get(token=token)
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
        # User is already authenticated by Alliance Auth SSO
        user = request.user

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

        # Deactivate any auto-kick schedule for this user
        try:
            auto_kick_schedule = AutoKickSchedule.objects.filter(
                discord_id=onboarding_token.discord_id,
                is_active=True
            ).first()
            if auto_kick_schedule:
                auto_kick_schedule.deactivate()
                logger.info(f"Deactivated auto-kick schedule for authenticated user {onboarding_token.discord_username}")
        except Exception as e:
            logger.error(f"Error deactivating auto-kick schedule: {e}")

        # Clear the onboarding token and bypass flag from session
        del request.session['onboarding_token']
        if 'discord_onboarding_bypass_email' in request.session:
            del request.session['discord_onboarding_bypass_email']

        # Trigger Discord group/role update
        try:
            from .tasks import process_completed_onboarding
            process_completed_onboarding.delay(onboarding_token.id)
        except Exception as e:
            logger.error(f"Error triggering completed onboarding processing: {e}")

        # Send success notification to auto-kick log channel
        if DISCORD_ONBOARDING_KICK_LOG_CHANNEL_ID:
            try:
                from .tasks import log_successful_authentication
                log_successful_authentication.delay(onboarding_token.id)
            except Exception as e:
                logger.error(f"Error sending authentication success notification: {e}")

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


# Custom SSO login view for Discord onboarding with email bypass
from esi.decorators import token_required
from django.conf import settings
from django.contrib.auth.models import User


@token_required(new=True, scopes=settings.LOGIN_TOKEN_SCOPES)
def discord_onboarding_sso_login(request, token):
    """Custom SSO login that handles email verification bypass for Discord onboarding."""
    
    # Check if this is a Discord onboarding request
    bypass_email = request.session.get('discord_onboarding_bypass_email', False)
    
    try:
        # Use the original sso_login logic
        user = authenticate(token=token)
        if user:
            token.user = user
            from esi.models import Token
            if Token.objects.exclude(pk=token.pk).equivalent_to(token).require_valid().exists():
                token.delete()
            else:
                token.save()
            
            # If user is active, login and redirect
            if user.is_active:
                login(request, user)
                return redirect(request.POST.get('next', request.GET.get('next', 'authentication:dashboard')))
            
            # If user is not active, they should be activated by our signal handler if bypass is enabled
            # Wait a moment for the signal to process, then check again
            elif bypass_email and DISCORD_ONBOARDING_BYPASS_EMAIL_VERIFICATION:
                import time
                time.sleep(0.1)  # Brief pause for signal processing
                user.refresh_from_db()
                if user.is_active:
                    login(request, user)
                    return redirect(request.POST.get('next', request.GET.get('next', 'authentication:dashboard')))
                else:
                    # Fallback: activate directly if signal didn't work
                    user.is_active = True
                    user.save()
                    login(request, user)
                    logger.info(f"Activated user {user.username} via Discord onboarding email bypass (fallback)")
                    return redirect(request.POST.get('next', request.GET.get('next', 'authentication:dashboard')))
            
            # If user has no email, redirect to registration
            elif not user.email:
                # Store the new user PK in the session to enable us to identify the registering user
                request.session['registration_uid'] = user.pk
                # Go to custom registration that handles email bypass
                return redirect('discord_onboarding:registration')
        
        # Logging in with an alt is not allowed due to security concerns.
        token.delete()
        messages.error(
            request,
            _(
                'Unable to authenticate as the selected character. '
                'Please log in with the main character associated with this account.'
            )
        )
        return redirect(settings.LOGIN_URL)
    except Exception as e:
        logger.error(f"Error in discord_onboarding_sso_login: {e}")
        return redirect(settings.LOGIN_URL)


def discord_onboarding_registration(request):
    """Custom registration view for Discord onboarding that handles email bypass."""
    from django.contrib.auth.forms import UserCreationForm
    from django.http import HttpResponseBadRequest
    
    # Check if this is a Discord onboarding request
    bypass_email = request.session.get('discord_onboarding_bypass_email', False)
    registration_uid = request.session.get('registration_uid')
    
    if not bypass_email or not DISCORD_ONBOARDING_BYPASS_EMAIL_VERIFICATION:
        # Redirect to normal registration if bypass is not enabled
        return redirect('registration_register')
    
    if not registration_uid:
        return HttpResponseBadRequest("Invalid registration session")
    
    try:
        # Get the user that was created during SSO
        user = User.objects.get(pk=registration_uid)
        
        if request.method == 'POST':
            # For Discord onboarding, we skip email verification
            # Just activate the user and login
            user.is_active = True
            user.save()
            
            # Clear the registration session
            if 'registration_uid' in request.session:
                del request.session['registration_uid']
            
            login(request, user)
            logger.info(f"Registered and activated user {user.username} via Discord onboarding")
            
            # Send success notification if there's an onboarding token session
            onboarding_token = request.session.get('onboarding_token')
            if onboarding_token and DISCORD_ONBOARDING_KICK_LOG_CHANNEL_ID:
                try:
                    from .tasks import log_successful_authentication
                    token_obj = OnboardingToken.objects.filter(token=onboarding_token).first()
                    if token_obj:
                        log_successful_authentication.delay(token_obj.id)
                except Exception as e:
                    logger.error(f"Error sending registration success notification: {e}")
            
            # Redirect to the callback URL
            return redirect(request.GET.get('next', 'authentication:dashboard'))
        
        # For GET request, show a simple form or auto-submit
        # Since we're bypassing email, we can auto-submit
        return render(request, 'discord_onboarding/auto_register.html', {
            'user': user,
            'next': request.GET.get('next', 'authentication:dashboard')
        })
        
    except User.DoesNotExist:
        return HttpResponseBadRequest("Invalid registration user")
