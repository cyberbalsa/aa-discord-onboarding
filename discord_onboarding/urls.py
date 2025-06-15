"""URLs for Discord Onboarding."""

from django.urls import path

from . import views

app_name = 'discord_onboarding'

urlpatterns = [
    path('', views.index, name='index'),
    path('start/<str:token>/', views.onboarding_start, name='start'),
    path('callback/', views.onboarding_callback, name='callback'),
    path('sso/login/', views.discord_onboarding_sso_login, name='sso_login'),
    path('registration/', views.discord_onboarding_registration, name='registration'),
]
