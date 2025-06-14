"""URLs for Discord Onboarding."""

from django.urls import path

from . import views

app_name = 'discord_onboarding'

urlpatterns = [
    path('', views.index, name='index'),
    path('start/<str:token>/', views.onboarding_start, name='start'),
    path('callback/', views.onboarding_callback, name='callback'),
]
