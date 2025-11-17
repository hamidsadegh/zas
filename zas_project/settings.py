# Django settings for zas_project project.

from pathlib import Path
import os
import environ # type: ignore

# Initialize environment variables
env = environ.Env()
environ.Env.read_env()  # reads .env

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-axas6dz8ha_v$3(xxk3h4&6736=(%yb_bws(9+!ad!64$0ltf&'

# SECURITY WARNING: don't run with debug turned on in production!
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        # General application logs (framework, internal actions)
        "application_file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "/var/log/zas/django/application.log",
            "formatter": "standard",
        },
        # Errors & exceptions (only ERROR+)
        "error_file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": "/var/log/zas/django/errors.log",
            "formatter": "standard",
        },
        # HTTP requests (GET/POST/PUT/DELETE)
        "requests_file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "/var/log/zas/django/requests.log",
            "formatter": "standard",
        },
        # Security logs (auth failures, permissions, CSRF)
        "security_file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "/var/log/zas/django/security.log",
            "formatter": "standard",
        },
    },

    "loggers": {
        # Django core
        "django": {
            "handlers": ["application_file"],
            "level": "INFO",
            "propagate": True,
        },
        # ALL HTTP requests (very important!)
        "django.request": {
            "handlers": ["requests_file", "error_file"],
            "level": "INFO",        # ← INFO logs normal requests
            "propagate": False,
        },
        # Security subsystem
        "django.security": {
            "handlers": ["security_file"],
            "level": "INFO",
            "propagate": False,
        },
        # Django server (only used for error tracebacks)
        "django.server": {
            "handlers": ["error_file"],
            "level": "ERROR",
            "propagate": False,
        },
        # Django REST Framework log channel
        "rest_framework": {
            "handlers": ["requests_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',

    # Local apps
    'accounts',
    'vlans',
    'devices',
    'automation',
    'django_crontab',
    'django_celery_beat',

]

CRONJOBS = [
    # Every 15 minutes: collect telemetry
    ('*/15 * * * *', 'automation.tasks.collect_all_telemetry'),
    # Every night at 2 AM: run configuration backups
    ('0 2 * * *', 'automation.tasks.run_scheduled_backups'),
]

# Celery Configuration Options
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'  # if using Redis
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'
CELERY_BEAT_SCHEDULE = {
    'check-reachability-every-10-seconds': {
        'task': 'automation.tasks.check_devices_reachability',
        'schedule': 1000.0, # every 10 seconds
    },
}

LOGIN_URL = '/admin/login/'

REST_FRAMEWORK = {
    'DEFAULT_METADATA_CLASS': 'rest_framework.metadata.SimpleMetadata',
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # require login for all API views
    ],
}

AUTHENTICATION_BACKENDS = [
    'accounts.auth_backends.IseTacacsBackend',
    'django.contrib.auth.backends.ModelBackend',
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

ROOT_URLCONF = 'zas_project.urls'

TEMPLATES =[
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "zas_project", "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = 'zas_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DATABASE_NAME', default='zas'),
        'USER': env('DATABASE_USER', default='zasuser'),
        'PASSWORD': env('DATABASE_PASSWORD', default='zas_pass'),
        'HOST': env('DATABASE_HOST', default='127.0.0.1'),
        'PORT': env('DATABASE_PORT', default='3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        }
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


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Berlin'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
