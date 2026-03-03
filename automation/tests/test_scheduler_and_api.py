from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django_celery_beat.models import IntervalSchedule, PeriodicTask
from celery.exceptions import CeleryError
from rest_framework.test import APIClient

from accounts.models.system_settings import SystemSettings
from automation.models import AutomationSchedule
from automation.services.scheduler_sync import (
    REACHABILITY_NAME,
    REACHABILITY_TASK,
    remove_schedule,
    sync_reachability_from_system_settings,
    sync_schedule,
)


@pytest.fixture
def api_client():
    user = get_user_model().objects.create_user(username="api-user", password="pass")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_sync_schedule_creates_interval_periodic_task():
    schedule = AutomationSchedule.objects.create(
        name="Reachability Poller",
        task_name=REACHABILITY_TASK,
        schedule_type=AutomationSchedule.ScheduleType.INTERVAL,
        interval_seconds=300,
        enabled=True,
    )

    periodic_task = sync_schedule(schedule)
    schedule.refresh_from_db()

    assert schedule.periodic_task == periodic_task
    assert periodic_task.task == REACHABILITY_TASK
    assert periodic_task.interval.every == 300
    assert periodic_task.crontab is None


@pytest.mark.django_db
def test_sync_schedule_reuses_existing_periodic_task_with_same_name():
    old_interval = IntervalSchedule.objects.create(
        every=30,
        period=IntervalSchedule.SECONDS,
    )
    existing = PeriodicTask.objects.create(
        name="Nightly Configuration Backup",
        task="outdated.task",
        interval=old_interval,
        enabled=False,
    )
    schedule = AutomationSchedule.objects.create(
        name="Nightly Configuration Backup",
        task_name="automation.tasks.run_scheduled_config_backup",
        schedule_type=AutomationSchedule.ScheduleType.CRONTAB,
        minute="0",
        hour="4",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        enabled=True,
    )

    periodic_task = sync_schedule(schedule)
    schedule.refresh_from_db()
    existing.refresh_from_db()

    assert periodic_task.pk == existing.pk
    assert schedule.periodic_task == existing
    assert existing.task == "automation.tasks.run_scheduled_config_backup"
    assert existing.enabled is True
    assert existing.interval is None
    assert existing.crontab is not None


@pytest.mark.django_db
def test_sync_reachability_from_system_settings_updates_existing_schedule():
    AutomationSchedule.objects.create(
        name=REACHABILITY_NAME,
        task_name=REACHABILITY_TASK,
        schedule_type=AutomationSchedule.ScheduleType.INTERVAL,
        interval_seconds=60,
        enabled=False,
    )
    settings = SystemSettings.get()
    settings.reachability_interval_minutes = 15
    settings.save(update_fields=["reachability_interval_minutes"])

    schedule = sync_reachability_from_system_settings(settings)
    schedule.refresh_from_db()

    assert schedule.interval_seconds == 900
    assert schedule.enabled is True
    assert schedule.periodic_task is not None
    assert schedule.periodic_task.interval.every == 900


@pytest.mark.django_db
def test_remove_schedule_detaches_and_deletes_periodic_task():
    schedule = AutomationSchedule.objects.create(
        name="Delete Me",
        task_name=REACHABILITY_TASK,
        schedule_type=AutomationSchedule.ScheduleType.INTERVAL,
        interval_seconds=120,
    )
    periodic_task = sync_schedule(schedule)

    remove_schedule(schedule)
    schedule.refresh_from_db()

    assert schedule.periodic_task is None
    assert PeriodicTask.objects.filter(pk=periodic_task.pk).exists() is False


@pytest.mark.django_db
def test_run_now_returns_accepted_response(api_client):
    schedule = AutomationSchedule.objects.create(
        name="Manual Reachability",
        task_name=REACHABILITY_TASK,
        schedule_type=AutomationSchedule.ScheduleType.INTERVAL,
        interval_seconds=60,
    )

    with patch(
        "api.v1.automation.views.current_app.send_task",
        return_value=SimpleNamespace(id="celery-123"),
    ) as mock_send_task:
        response = api_client.post(f"/api/v1/automation/schedules/{schedule.pk}/run/")

    assert response.status_code == 202
    assert response.json()["celery_id"] == "celery-123"
    mock_send_task.assert_called_once_with(REACHABILITY_TASK)


@pytest.mark.django_db
def test_run_now_returns_500_when_celery_raises(api_client):
    schedule = AutomationSchedule.objects.create(
        name="Failing Reachability",
        task_name=REACHABILITY_TASK,
        schedule_type=AutomationSchedule.ScheduleType.INTERVAL,
        interval_seconds=60,
    )

    with patch("api.v1.automation.views.current_app.send_task", side_effect=CeleryError("boom")):
        response = api_client.post(f"/api/v1/automation/schedules/{schedule.pk}/run/")

    assert response.status_code == 500
    assert response.json()["status"] == "error"


@pytest.mark.django_db
def test_celery_health_returns_200_with_worker_status(api_client):
    interval = IntervalSchedule.objects.create(every=60, period=IntervalSchedule.SECONDS)
    PeriodicTask.objects.create(
        name="Reachability Poller",
        task=REACHABILITY_TASK,
        interval=interval,
        enabled=True,
    )
    fake_inspector = SimpleNamespace(ping=lambda: {"worker@node": {"ok": "pong"}})
    fake_app = SimpleNamespace(
        tasks={"automation.tasks.run_scheduled_reachability": object(), "other.task": object()},
        control=SimpleNamespace(inspect=lambda timeout=1.0: fake_inspector),
    )

    with patch("api.v1.automation.views.current_app", fake_app):
        response = api_client.get("/api/v1/automation/celery/health/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["broker_ok"] is True
    assert payload["workers_responding"] == ["worker@node"]
    assert payload["registered_tasks"] == ["automation.tasks.run_scheduled_reachability"]
    assert payload["periodic_tasks"][0]["name"] == "Reachability Poller"


@pytest.mark.django_db
def test_celery_health_returns_503_without_workers(api_client):
    fake_inspector = SimpleNamespace(ping=lambda: {})
    fake_app = SimpleNamespace(
        tasks={"automation.tasks.run_scheduled_reachability": object()},
        control=SimpleNamespace(inspect=lambda timeout=1.0: fake_inspector),
    )

    with patch("api.v1.automation.views.current_app", fake_app):
        response = api_client.get("/api/v1/automation/celery/health/")

    assert response.status_code == 503
    assert response.json()["broker_ok"] is False
