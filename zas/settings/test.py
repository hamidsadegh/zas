# zas/settings/test.py
from .base import *

DEBUG = True

DATABASES["default"]["TEST"] = {
    "NAME": "test_zas",
    "MIRROR": None,
    "CHARSET": "utf8mb4",
    "COLLATION": "utf8mb4_unicode_ci",
    "MIGRATE": True,
}