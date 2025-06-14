"""
Test URLs for AA Discord Onboarding
"""

from django.urls import path, include

urlpatterns = [
    path('discord-onboarding/', include('discord_onboarding.urls')),
]