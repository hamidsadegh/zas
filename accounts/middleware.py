import time

from django.conf import settings as django_settings
from django.contrib.auth import logout
from django.shortcuts import redirect

from accounts.services.settings_service import (
    get_auto_logout_timeout_seconds,
    get_system_settings,
)


class AutoLogoutMiddleware:
    LAST_ACTIVITY_SESSION_KEY = "last_activity_at"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.auto_logout_timeout_seconds = 0
        request.auto_logout_timeout_minutes = 0

        if not request.user.is_authenticated:
            return self.get_response(request)

        timeout_settings = get_system_settings()
        timeout_seconds = get_auto_logout_timeout_seconds(timeout_settings)
        request.auto_logout_timeout_seconds = timeout_seconds
        request.auto_logout_timeout_minutes = timeout_settings.auto_logout_idle_minutes

        now = int(time.time())
        last_activity = request.session.get(self.LAST_ACTIVITY_SESSION_KEY)

        if last_activity is not None and now - int(last_activity) >= timeout_seconds:
            logout(request)
            return redirect(f"{django_settings.LOGIN_URL}?timeout=1")

        request.session[self.LAST_ACTIVITY_SESSION_KEY] = now
        response = self.get_response(request)
        return response
