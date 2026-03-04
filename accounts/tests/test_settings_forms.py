import pytest

from accounts.forms.settings_form import AllowLocalSuperusersForm
from accounts.models import SystemSettings


@pytest.mark.django_db
def test_allow_local_superusers_form_accepts_auto_logout_within_bounds():
    settings = SystemSettings.get()
    form = AllowLocalSuperusersForm(
        data={
            "allow_local_superusers": "on",
            "auto_logout_idle_minutes": 30,
        },
        instance=settings,
    )

    assert form.is_valid() is True


@pytest.mark.django_db
@pytest.mark.parametrize("minutes", [4, 61])
def test_allow_local_superusers_form_rejects_auto_logout_outside_bounds(minutes):
    settings = SystemSettings.get()
    form = AllowLocalSuperusersForm(
        data={
            "allow_local_superusers": "on",
            "auto_logout_idle_minutes": minutes,
        },
        instance=settings,
    )

    assert form.is_valid() is False
    assert "auto_logout_idle_minutes" in form.errors
