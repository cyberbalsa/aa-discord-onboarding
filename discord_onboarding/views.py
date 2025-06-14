import logging

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.services.modules.discord.models import DiscordUser
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .models import DiscordAuthRequest, DiscordOnboardingStats
from .tasks import send_auth_success_notification

logger = logging.getLogger(__name__)


@login_required
@permission_required("aadiscordbot.basic_access")
def index(request):
    """
    Discord Onboarding dashboard
    """
    # Get recent statistics
    recent_stats = DiscordOnboardingStats.objects.all()[:7]

    # Get user's authentication status
    user_discord_linked = False
    user_discord_id = None
    try:
        discord_user = DiscordUser.objects.get(user=request.user)
        user_discord_linked = True
        user_discord_id = discord_user.uid
    except DiscordUser.DoesNotExist:
        pass

    # Get recent auth requests
    recent_requests = DiscordAuthRequest.objects.order_by("-created_at")[:10]

    context = {
        "recent_stats": recent_stats,
        "user_discord_linked": user_discord_linked,
        "user_discord_id": user_discord_id,
        "recent_requests": recent_requests,
    }

    return render(request, "discord_onboarding/index.html", context)


def auth_start(request, token):
    """
    Initial authentication view - validates token and redirects to EVE SSO
    """
    try:
        auth_request = get_object_or_404(DiscordAuthRequest, token=token)
    except DiscordAuthRequest.DoesNotExist:
        return render(
            request,
            "discord_onboarding/error.html",
            {
                "error_title": "Invalid Authentication Link",
                "error_message": "This authentication link is not valid or has expired.",
            },
        )

    if not auth_request.is_valid:
        return render(
            request,
            "discord_onboarding/error.html",
            {
                "error_title": "Authentication Link Expired",
                "error_message": (
                    "This authentication link has expired. "
                    "Please request a new one using the /auth command in Discord."
                ),
            },
        )

    # Store the auth request token in session for callback
    request.session["discord_auth_token"] = str(auth_request.token)

    # Redirect to EVE SSO
    # Use Alliance Auth's built-in EVE SSO authentication
    return HttpResponseRedirect(reverse("authentication:login"))


def auth_callback(request, token):
    """
    Handle EVE SSO callback and complete Discord authentication
    """
    # Get the auth request from session
    auth_token = request.session.get("discord_auth_token")
    if not auth_token:
        return render(
            request,
            "discord_onboarding/error.html",
            {
                "error_title": "Authentication Error",
                "error_message": (
                    "Authentication session expired. " "Please start the process again."
                ),
            },
        )

    try:
        auth_request = DiscordAuthRequest.objects.get(token=auth_token)
    except DiscordAuthRequest.DoesNotExist:
        return render(
            request,
            "discord_onboarding/error.html",
            {
                "error_title": "Authentication Error",
                "error_message": (
                    "Invalid authentication session. " "Please start the process again."
                ),
            },
        )

    if not auth_request.is_valid:
        return render(
            request,
            "discord_onboarding/error.html",
            {
                "error_title": "Authentication Expired",
                "error_message": (
                    "This authentication request has expired. "
                    "Please request a new link."
                ),
            },
        )

    # Check if user is authenticated
    if not request.user.is_authenticated:
        return render(
            request,
            "discord_onboarding/error.html",
            {
                "error_title": "Authentication Required",
                "error_message": "Please log in with your EVE Online character first.",
            },
        )

    # Get character information from the authenticated user
    try:
        # Get the user's main character
        character_ownership = CharacterOwnership.objects.filter(
            user=request.user
        ).first()
        if not character_ownership:
            return render(
                request,
                "discord_onboarding/error.html",
                {
                    "error_title": "No Character Found",
                    "error_message": "No EVE Online character associated with your account.",
                },
            )

        eve_character = character_ownership.character

    except Exception as e:
        logger.error(f"Error retrieving character information: {e}")
        return render(
            request,
            "discord_onboarding/error.html",
            {
                "error_title": "Character Information Error",
                "error_message": (
                    "Unable to retrieve character information from EVE Online. "
                    "Please try again."
                ),
            },
        )

    # Use the authenticated user
    user = request.user

    # Link Discord user to Alliance Auth user
    try:
        discord_user, created = DiscordUser.objects.get_or_create(
            uid=auth_request.discord_user_id, defaults={"user": user}
        )

        if not created and discord_user.user != user:
            # Update existing Discord user linkage
            discord_user.user = user
            discord_user.save()

        logger.info(
            f"Linked Discord user {auth_request.discord_user_id} "
            f"to Alliance Auth user {user.username}"
        )

    except Exception as e:
        logger.error(f"Error linking Discord user: {e}")
        return render(
            request,
            "discord_onboarding/error.html",
            {
                "error_title": "Discord Linking Error",
                "error_message": (
                    "Authentication successful but unable to link your Discord account. "
                    "Please contact an administrator."
                ),
            },
        )

    # Complete the authentication request
    auth_request.complete_auth(user, eve_character)

    # Clean up session
    if "discord_auth_token" in request.session:
        del request.session["discord_auth_token"]

    # Send success notification to Discord (async task)
    try:
        send_auth_success_notification.delay(
            discord_user_id=auth_request.discord_user_id,
            character_name=eve_character.character_name,
            guild_id=auth_request.guild_id,
        )
    except Exception as e:
        logger.warning(f"Failed to send Discord notification: {e}")

    # Render success page
    return render(
        request,
        "discord_onboarding/success.html",
        {
            "character_name": eve_character.character_name,
            "corporation_name": eve_character.corporation_name,
            "alliance_name": eve_character.alliance_name,
        },
    )


def auth_status(request, token):
    """
    Check the status of an authentication request
    """
    try:
        auth_request = get_object_or_404(DiscordAuthRequest, token=token)
    except DiscordAuthRequest.DoesNotExist:
        return HttpResponseBadRequest("Invalid token")

    status_data = {
        "completed": auth_request.completed,
        "expired": auth_request.is_expired,
        "valid": auth_request.is_valid,
        "created_at": auth_request.created_at.isoformat(),
        "expires_at": auth_request.expires_at.isoformat(),
    }

    if auth_request.completed:
        status_data["character_name"] = (
            auth_request.eve_character.character_name
            if auth_request.eve_character
            else None
        )

    return JsonResponse(status_data)
