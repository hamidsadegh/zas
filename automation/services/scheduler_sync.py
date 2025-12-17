# automation/services/scheduler_sync.py

import logging
from typing import Optional
from django.utils import timezone

from automation.models import AutomationSchedule
from accounts.models.system_settings import SystemSettings
from django_celery_beat.models import (
    PeriodicTask,
    IntervalSchedule,
    CrontabSchedule,
)

REACHABILITY_TASK = "automation.tasks.run_scheduled_reachability"
REACHABILITY_NAME = "Reachability Poller"

logger = logging.getLogger(__name__)


def _ensure_interval_schedule(seconds: int) -> IntervalSchedule:
    return IntervalSchedule.objects.get_or_create(
        every=seconds,
        period=IntervalSchedule.SECONDS,
    )[0]


def _ensure_crontab_schedule(schedule: AutomationSchedule) -> CrontabSchedule:
    return CrontabSchedule.objects.get_or_create(
        minute=schedule.minute,
        hour=schedule.hour,
        day_of_week=schedule.day_of_week,
        day_of_month=schedule.day_of_month,
        month_of_year=schedule.month_of_year,
    )[0]


def sync_schedule(schedule: AutomationSchedule) -> PeriodicTask:
    """
    Ensure there is a matching django_celery_beat PeriodicTask for this AutomationSchedule.
    """
    if schedule.schedule_type == AutomationSchedule.ScheduleType.INTERVAL:
        if not schedule.interval_seconds or schedule.interval_seconds <= 0:
            raise ValueError("interval_seconds must be > 0 for interval schedules.")
        interval = _ensure_interval_schedule(schedule.interval_seconds)
        crontab = None
    else:
        crontab = _ensure_crontab_schedule(schedule)
        interval = None

    pt: Optional[PeriodicTask] = schedule.periodic_task

    if pt is None:
        # Try to re-use an existing PeriodicTask with the same name
        pt, created = PeriodicTask.objects.get_or_create(
            name=schedule.name,
            defaults={
                "task": schedule.task_name,
                "interval": interval,
                "crontab": crontab,
                "enabled": schedule.enabled,
            },
        )

        # If it already existed, make sure it is fully synced
        if not created:
            pt.task = schedule.task_name
            pt.interval = interval
            pt.crontab = crontab
            pt.enabled = schedule.enabled
            pt.clocked = None
            pt.one_off = False
            pt.start_time = pt.start_time or timezone.now()
            pt.save()

        schedule.periodic_task = pt
        schedule.save(update_fields=["periodic_task"])

        logger.info("Linked PeriodicTask %s to schedule %s", pt.name, schedule.id)
    else:
        pt.name = schedule.name
        pt.task = schedule.task_name
        pt.enabled = schedule.enabled
        pt.interval = interval
        pt.crontab = crontab
        pt.clocked = None
        pt.one_off = False
        pt.start_time = pt.start_time or timezone.now()
        pt.save()
        logger.info("Updated PeriodicTask %s for schedule %s", pt.name, schedule.id)

    return pt


def sync_reachability_from_system_settings(settings: SystemSettings) -> AutomationSchedule:
    """
    Sync reachability schedule from SystemSettings into AutomationSchedule
    and ensure celery-beat is updated.
    """
    interval_seconds = settings.reachability_interval_minutes * 60

    schedule, _ = AutomationSchedule.objects.get_or_create(
        task_name=REACHABILITY_TASK,
        defaults={
            "name": REACHABILITY_NAME,
            "schedule_type": AutomationSchedule.ScheduleType.INTERVAL,
            "interval_seconds": interval_seconds,
            "enabled": True,
        },
    )

    changed = False

    if schedule.task_name != REACHABILITY_TASK:
        schedule.task_name = REACHABILITY_TASK
        changed = True

    if schedule.interval_seconds != interval_seconds:
        schedule.interval_seconds = interval_seconds
        changed = True

    if not schedule.enabled:
        schedule.enabled = True
        changed = True

    if changed:
        schedule.save()  # ← NO SIGNALS ANYMORE

    # Explicitly sync celery-beat
    sync_schedule(schedule)

    return schedule


def sync_config_backup_schedule() -> AutomationSchedule:
    """
    Ensure the nightly configuration backup schedule exists and is synced.
    """
    schedule, _ = AutomationSchedule.objects.get_or_create(
        name="Nightly Configuration Backup",
        defaults={
            "task_name": "automation.tasks.run_scheduled_config_backup",
            "schedule_type": AutomationSchedule.ScheduleType.CRONTAB,
            "minute": "0",
            "hour": "4",
            "day_of_week": "*",
            "day_of_month": "*",
            "month_of_year": "*",
            "enabled": True,
        },
    )

    # If schedule already exists, enforce correct values (idempotent)
    schedule.task_name = "automation.tasks.run_scheduled_config_backup"
    schedule.schedule_type = AutomationSchedule.ScheduleType.CRONTAB
    schedule.minute = "0"
    schedule.hour = "4"
    schedule.day_of_week = "*"
    schedule.day_of_month = "*"
    schedule.month_of_year = "*"
    schedule.enabled = True
    schedule.save()

    sync_schedule(schedule)
    return schedule


def sync_reachability_cleanup_schedule(days: int = 7):
    schedule, _ = AutomationSchedule.objects.get_or_create(
        name="Reachability History Cleanup",
        defaults={
            "task_name": "automation.tasks.cleanup_reachability_history",
            "schedule_type": AutomationSchedule.ScheduleType.CRONTAB,
            "minute": "30",
            "hour": "3",
            "day_of_week": "*",
            "day_of_month": "*",
            "month_of_year": "*",
            "enabled": True,
        },
    )

    schedule.save()
    sync_schedule(schedule)


def remove_schedule(schedule: AutomationSchedule) -> None:
    pt = schedule.periodic_task
    if pt:
        logger.info("Deleting PeriodicTask %s for schedule %s", pt.name, schedule.id)
        schedule.periodic_task = None
        schedule.save(update_fields=["periodic_task"])
        pt.delete()
