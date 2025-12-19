# zas/settings/test.py
from .base import *

DEBUG = True

DATABASES["default"]["TEST"] = {
    "NAME": "test_zas",
}
