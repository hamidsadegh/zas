# Django settings for zas project.

from pathlib import Path
from environ import Env 
import os
import sys


# Check Python Version
def enforce_python_version():
    if sys.version_info >= (3, 12):
        raise RuntimeError(
            "ZAS currently requires Python < 3.12 due to SNMP (pysnmp/asyncore)."
        )

    

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Initialize environment variables
env = Env()
env.read_env(os.path.join(BASE_DIR, '.env'))
 # reads .env


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-axas6dz8ha_v$3(xxk3h4&6736=(%yb_bws(9+!ad!64$0ltf&'

# Encryption key for django-encrypted-model-fields
FIELD_ENCRYPTION_KEY = env('FIELD_ENCRYPTION_KEY')

# Allowed Hosts
ALLOWED_HOSTS = ['*']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        # General application logs (framework, internal actions)
        'application_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/zas/django/application.log',
            'formatter': 'standard',
        },
        # Errors & exceptions (only ERROR+)
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/var/log/zas/django/errors.log',
            'formatter': 'standard',
        },
        # HTTP requests (GET/POST/PUT/DELETE)
        'requests_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/zas/django/requests.log',
            'formatter': 'standard',
        },
        # Security logs (auth failures, permissions, CSRF)
        'security_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/zas/django/security.log',
            'formatter': 'standard',
        },
    },

    'loggers': {
        # Django core
        'django': {
            'handlers': ['application_file'],
            'level': 'INFO',
            'propagate': True,
        },
        # ALL HTTP requests (very important!)
        'django.request': {
            'handlers': ['requests_file', 'error_file'],
            'level': 'INFO',        # ← INFO logs normal requests
            'propagate': False,
        },
        # Security subsystem
        'django.security': {
            'handlers': ['security_file'],
            'level': 'INFO',
            'propagate': False,
        },
        # Django server (only used for error tracebacks)
        'django.server': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        # Django REST Framework log channel
        'rest_framework': {
            'handlers': ['requests_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}


# REST_FRAMEWORK = {
#     'DEFAULT_FILTER_BACKENDS': [
#         'django_filters.rest_framework.DjangoFilterBackend',
#     ],
# }


# Application definition

INSTALLED_APPS = [
    # Default Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'django_filters',
    'channels',

    # Local apps
    'core',
    'ipam',
    'dcim',
    'accounts',
    'automation',
    'django_crontab',
    'django_celery_beat',

]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Berlin'
USE_I18N = True
USE_TZ = True

# Celery Configuration Options
CELERY_BROKER_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = env("REDIS_URL", default="redis://127.0.0.1:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Tell Celery beat to load schedules from database
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers.DatabaseScheduler'

# Authentication settings
LOGIN_URL = '/admin/login/'
LOGOUT_REDIRECT_URL = '/admin/login/'

AUTHENTICATION_BACKENDS = [
    'accounts.auth_backends.IseTacacsBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_METADATA_CLASS': 'rest_framework.metadata.SimpleMetadata',
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # require login for all API views
    ],
}



MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'zas.urls'

TEMPLATES =[
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'zas', 'templates')],
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

ASGI_APPLICATION = 'zas.asgi.application'
WSGI_APPLICATION = 'zas.wsgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [
                env('REDIS_URL', default='redis://127.0.0.1:6379/1'),
            ],
        },
    },
}


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DATABASE_NAME', default='zas'),
        'USER': env('DATABASE_USER', default='zasuser'),
        'PASSWORD': env('DATABASE_PASSWORD', default='zas_pass'),
        'HOST': env('DATABASE_HOST', default='127.0.0.1'),
        'PORT': env('DATABASE_PORT', default='5432'),
        'OPTIONS': {
            "options": "-c timezone=UTC",
        },
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
