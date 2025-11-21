import pytest

from accounts.models import SystemSettings


@pytest.mark.django_db
def test_systemsettings_get_returns_singleton():
    first = SystemSettings.get()
    first.tacacs_enabled = True
    first.tacacs_server_ip = "192.0.2.1"
    first.save()

    second = SystemSettings.get()

    assert first.pk == 1
    assert second.pk == first.pk
    assert second.tacacs_enabled is True
    assert second.tacacs_server_ip == "192.0.2.1"
    assert SystemSettings.objects.count() == 1


@pytest.mark.django_db
def test_systemsettings_get_creates_default_when_missing():
    SystemSettings.objects.all().delete()

    created = SystemSettings.get()

    assert created.pk == 1
    assert created.tacacs_enabled is False


@pytest.mark.django_db
def test_reachability_settings_persist():
    settings = SystemSettings.get()
    settings.reachability_ping_enabled = False
    settings.reachability_snmp_enabled = False
    settings.reachability_ssh_enabled = True
    settings.reachability_telemetry_enabled = True
    settings.reachability_interval_minutes = 60
    settings.save()

    refreshed = SystemSettings.get()
    checks = refreshed.get_reachability_checks()

    assert checks == {
        "ping": False,
        "snmp": False,
        "ssh": True,
        "telemetry": True,
    }
    assert refreshed.reachability_interval_minutes == 60
