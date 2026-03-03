from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory

from accounts.auth_backends import IseTacacsBackend


def _request_with_session():
    request = RequestFactory().post("/admin/login/")
    SessionMiddleware(lambda req: None).process_request(request)
    request.session.save()
    request.user = AnonymousUser()
    return request


def _settings(**overrides):
    defaults = {
        "tacacs_enabled": True,
        "tacacs_server_ip": "192.0.2.10",
        "tacacs_port": 49,
        "tacacs_key": "secret",
        "tacacs_authorization_service": "shell",
        "tacacs_retries": 2,
        "tacacs_session_timeout": 30,
        "allow_local_superusers": True,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@pytest.mark.django_db
def test_authenticate_falls_back_to_model_backend_when_tacacs_disabled(django_user_model):
    backend = IseTacacsBackend()
    request = _request_with_session()
    local_user = django_user_model.objects.create_user(
        username="local-user",
        password="local-pass",
    )

    with patch("accounts.auth_backends.get_system_settings", return_value=_settings(tacacs_enabled=False)):
        with patch.object(ModelBackend, "authenticate", return_value=local_user) as mock_auth:
            user = backend.authenticate(request, username="local-user", password="local-pass")

    assert user == local_user
    mock_auth.assert_called_once()


@pytest.mark.django_db
def test_authenticate_falls_back_to_local_auth_when_tacacs_unreachable(django_user_model):
    backend = IseTacacsBackend()
    request = _request_with_session()
    local_user = django_user_model.objects.create_user(
        username="fallback-user",
        password="fallback-pass",
    )

    with patch("accounts.auth_backends.get_system_settings", return_value=_settings()):
        with patch.object(backend, "_tacacs_auth", side_effect=TimeoutError("timeout")):
            with patch.object(ModelBackend, "authenticate", return_value=local_user) as mock_auth:
                user = backend.authenticate(request, username="fallback-user", password="fallback-pass")

    assert user == local_user
    mock_auth.assert_called_once()


@pytest.mark.django_db
def test_authenticate_returns_local_superuser_on_explicit_deny_when_allowed(django_user_model):
    backend = IseTacacsBackend()
    request = _request_with_session()
    local_superuser = django_user_model.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="super-secret",
    )

    with patch("accounts.auth_backends.get_system_settings", return_value=_settings(allow_local_superusers=True)):
        with patch.object(backend, "_tacacs_auth", return_value=(False, [])):
            user = backend.authenticate(request, username="admin", password="super-secret")

    assert user == local_superuser


@pytest.mark.django_db
def test_authenticate_syncs_shadow_user_and_stores_session_password():
    backend = IseTacacsBackend()
    request = _request_with_session()

    with patch("accounts.auth_backends.get_system_settings", return_value=_settings()):
        with patch.object(backend, "_tacacs_auth", return_value=(True, ["netops"])):
            user = backend.authenticate(request, username="tacacs-user", password="ssh-pass")

    assert user.username == "tacacs-user"
    assert user.is_staff is True
    assert user.has_usable_password() is False
    assert request.session["tacacs_password"] == "ssh-pass"


def test_parse_groups_from_avpairs_extracts_roles():
    groups = IseTacacsBackend._parse_groups_from_avpairs(
        [
            ("cisco-av-pair", "shell:roles=netops, noc "),
            ("shell:roles", "secops"),
            ("ignored", "value"),
            ("cisco-av-pair", b"shell:roles=ops"),
        ]
    )

    assert groups == ["netops", "noc", "secops", "ops"]
