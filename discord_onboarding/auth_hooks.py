from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook

from . import urls


class DiscordOnboardingMenuItemHook(MenuItemHook):
    def __init__(self):
        MenuItemHook.__init__(
            self,
            "Discord Onboarding",
            "fas fa-users",
            "discord_onboarding:index",
            navactive=["discord_onboarding:"],
        )

    def render(self, request):
        if request.user.has_perm("aadiscordbot.basic_access"):
            return MenuItemHook.render(self, request)
        return ""


@hooks.register("menu_item_hook")
def register_menu():
    return DiscordOnboardingMenuItemHook()


@hooks.register("url_hook")
def register_url():
    return UrlHook(urls, "discord_onboarding", r"^discord-onboarding/")


@hooks.register("discord_cogs_hook")
def register_cogs():
    return ["discord_onboarding.cogs.onboarding"]
