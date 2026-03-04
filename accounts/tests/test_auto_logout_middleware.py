from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory

from accounts.middleware import AutoLogoutMiddleware
from accounts.models import SystemSettings


def _request_with_session(path="/"):
    request = RequestFactory().get(path)
    SessionMiddleware(lambda req: None).process_request(request)
    request.session.save()
    return request


@pytest.mark.django_db
def test_auto_logout_middleware_tracks_activity(django_user_model):
    user = django_user_model.objects.create_user(username="operator", password="pass")
    settings = SystemSettings.get()
    settings.auto_logout_idle_minutes = 15
    settings.save(update_fields=["auto_logout_idle_minutes"])

    request = _request_with_session("/dashboard/")
    request.user = user

    middleware = AutoLogoutMiddleware(lambda req: HttpResponse("ok"))

    with patch("accounts.middleware.time.time", return_value=1_000):
        response = middleware(request)

    assert response.status_code == 200
    assert request.session[AutoLogoutMiddleware.LAST_ACTIVITY_SESSION_KEY] == 1_000
    assert request.auto_logout_timeout_minutes == 15
    assert request.auto_logout_timeout_seconds == 900


@pytest.mark.django_db
def test_auto_logout_middleware_logs_out_when_session_is_idle(django_user_model):
    user = django_user_model.objects.create_user(username="operator", password="pass")
    settings = SystemSettings.get()
    settings.auto_logout_idle_minutes = 5
    settings.save(update_fields=["auto_logout_idle_minutes"])

    request = _request_with_session("/devices/")
    request.user = user
    request.session[AutoLogoutMiddleware.LAST_ACTIVITY_SESSION_KEY] = 100

    middleware = AutoLogoutMiddleware(lambda req: HttpResponse("ok"))

    with patch("accounts.middleware.time.time", return_value=401):
        response = middleware(request)

    assert response.status_code == 302
    assert response.url == "/admin/login/?timeout=1"
    assert isinstance(request.user, AnonymousUser)
