from .base import *


DEBUG = True
DATABASES ['default']['TEST'] = {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "test_zas",
        "USER": "zasuser",
        "PASSWORD": "zas_pass",
        "HOST": "127.0.0.1",
        "PORT": "3306",
    
}

# Optional: speed up tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]