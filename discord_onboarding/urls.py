from django.urls import path

from . import views

app_name = "discord_onboarding"

urlpatterns = [
    path("", views.index, name="index"),
    path("auth/<uuid:token>/", views.auth_start, name="auth_start"),
    path("callback/<uuid:token>/", views.auth_callback, name="auth_callback"),
    path("status/<uuid:token>/", views.auth_status, name="auth_status"),
]
