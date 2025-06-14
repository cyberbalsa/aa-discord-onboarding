"""
Test settings for AA Discord Onboarding
"""

SECRET_KEY = 'test-secret-key-for-ci-only'

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'esi',
    'allianceauth',
    'allianceauth.authentication',
    'allianceauth.eveonline',
    'allianceauth.services',
    'allianceauth.services.modules.discord',
    'discord_onboarding',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'test_urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

STATIC_URL = '/static/'

# ESI Settings
ESI_SSO_CLIENT_ID = 'test-client-id'
ESI_SSO_CLIENT_SECRET = 'test-client-secret'
ESI_SSO_CALLBACK_URL = 'http://localhost:8000/sso/callback/'

# Celery (disable for tests)
CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

# Discord settings
DISCORD_GUILD_ID = 123456789
DISCORD_BOT_TOKEN = 'test-token'

# Plugin settings
DISCORD_ONBOARDING_BASE_URL = 'http://localhost:8000'
DISCORD_ONBOARDING_TOKEN_EXPIRY = 3600
DISCORD_ONBOARDING_ADMIN_ROLES = [123456789]

USE_TZ = True