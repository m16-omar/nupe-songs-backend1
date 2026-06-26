from pathlib import Path
import os
import environ

# Initialize environment variables reader
env = environ.Env(
    DEBUG=(bool, True),
    ALLOWED_HOSTS=(list, ['*']),
    USE_S3=(bool, False),
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Read .env file if it exists
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='django-insecure-s#x0sm1l#qelzu1^id5^mbt7n@j=w!ki+io=sp6q*_hmuy)srp')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env('ALLOWED_HOSTS')


# Application definition

INSTALLED_APPS = [
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.forms',
    'unfold.contrib.inlines',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'storages',
    
    # Local apps
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Needs to be at the top
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'nupe_songs.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'nupe_songs.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/db.sqlite3')
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

# Use timezone support
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files setup (for local storage fallback)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom Auth User Model
AUTH_USER_MODEL = 'api.CustomUser'

AUTHENTICATION_BACKENDS = [
    'api.backends.EmailOrUsernameModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# CORS Settings
CORS_ALLOW_ALL_ORIGINS = True  # In production, configure specific allowed hosts

# Django REST Framework Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

# Simple JWT settings
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

# S3 / DigitalOcean Spaces Cloud Storage Configuration
USE_S3 = env('USE_S3')
if USE_S3:
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
    
    # Optional S3 Custom Domain (for CDN like CloudFront or DigitalOcean Spaces CDN)
    AWS_S3_CUSTOM_DOMAIN = env('AWS_S3_CUSTOM_DOMAIN', default=None)
    
    # S3 Endpoint URL (e.g. for DigitalOcean Spaces or custom S3 compatible storage)
    AWS_S3_ENDPOINT_URL = env('AWS_S3_ENDPOINT_URL', default=None)
    
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    
    # Configure STORAGES (Django 4.2+)
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

# Unfold settings for Admin UI Customization (Tailwind CSS based)
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

UNFOLD = {
    "SITE_TITLE": _("Nupe Songs Admin"),
    "SITE_HEADER": _("Nupe Songs"),
    "SITE_URL": "/",
    "SITE_ICON": lambda request: STATIC_URL + "images/logo.jpg",
    "SITE_LOGO": lambda request: STATIC_URL + "images/logo.jpg",
    "SITE_SYMBOL": "library_music",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "DASHBOARD_CALLBACK": "api.utils.dashboard_callback",
    "COLORS": {
        "primary": {
            "50": "245 243 255",
            "100": "237 233 254",
            "200": "221 214 254",
            "300": "196 181 253",
            "400": "167 139 250",
            "500": "108 80 233",  # #6c50e9 (Primary Violet/Purple)
            "600": "99 74 214",
            "700": "84 62 181",
            "800": "69 51 148",
            "900": "56 41 120",
            "950": "39 29 84",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("Music Platform"),
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                    {
                        "title": _("Songs"),
                        "icon": "music_note",
                        "link": reverse_lazy("admin:api_song_changelist"),
                    },
                    {
                        "title": _("Albums"),
                        "icon": "album",
                        "link": reverse_lazy("admin:api_album_changelist"),
                    },
                    {
                        "title": _("Artists"),
                        "icon": "mic",
                        "link": reverse_lazy("admin:api_artist_changelist"),
                    },
                    {
                        "title": _("Genres"),
                        "icon": "category",
                        "link": reverse_lazy("admin:api_genre_changelist"),
                    },
                    {
                        "title": _("Lyrics"),
                        "icon": "lyrics",
                        "link": reverse_lazy("admin_lyrics"),
                    },
                    {
                        "title": _("Playlists"),
                        "icon": "playlist_play",
                        "link": reverse_lazy("admin:api_playlist_changelist"),
                    },
                ],
            },
            {
                "title": _("Users & Activity"),
                "items": [
                    {
                        "title": _("Users"),
                        "icon": "person",
                        "link": reverse_lazy("admin:api_customuser_changelist"),
                    },
                    {
                        "title": _("Subscriptions"),
                        "icon": "card_membership",
                        "link": reverse_lazy("admin:api_subscription_changelist"),
                    },
                    {
                        "title": _("Downloads"),
                        "icon": "download",
                        "link": reverse_lazy("admin:api_downloadlog_changelist"),
                    },
                    {
                        "title": _("Favorites"),
                        "icon": "favorite",
                        "link": reverse_lazy("admin_favorites"),
                    },
                    {
                        "title": _("Listening History"),
                        "icon": "history",
                        "link": reverse_lazy("admin:api_listeninghistory_changelist"),
                    },
                    {
                        "title": _("Analytics"),
                        "icon": "analytics",
                        "link": reverse_lazy("admin_analytics"),
                    },
                ],
            },
            {
                "title": _("Content & Marketing"),
                "items": [
                    {
                        "title": _("Banners"),
                        "icon": "image",
                        "link": reverse_lazy("admin:api_banner_changelist"),
                    },
                    {
                        "title": _("Announcements"),
                        "icon": "campaign",
                        "link": reverse_lazy("admin:api_announcement_changelist"),
                    },
                    {
                        "title": _("FAQs"),
                        "icon": "quiz",
                        "link": reverse_lazy("admin:api_faq_changelist"),
                    },
                ],
            },
            {
                "title": _("System"),
                "items": [
                    {
                        "title": _("Settings"),
                        "icon": "settings",
                        "link": reverse_lazy("admin_settings"),
                    },
                    {
                        "title": _("Activity Logs"),
                        "icon": "list_alt",
                        "link": reverse_lazy("admin:api_activitylog_changelist"),
                    },
                    {
                        "title": _("Backups"),
                        "icon": "backup",
                        "link": reverse_lazy("admin_backups"),
                    },
                    {
                        "title": _("Trash"),
                        "icon": "delete",
                        "link": reverse_lazy("admin_trash"),
                    },
                ],
            },
        ],
    },
    "STYLES": [
        lambda request: STATIC_URL + "css/unfold_custom.css",
    ],
}

