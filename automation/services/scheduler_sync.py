# automation/services/scheduler_sync.py

import logging
from typing import Optional

from django_celery_beat.models import (
    PeriodicTask,
    IntervalSchedule,
    CrontabSchedule,
)
from django.utils import timezone

from automation.models import AutomationSchedule

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
        pt = PeriodicTask.objects.create(
            name=schedule.name,
            task=schedule.task_name,
            interval=interval,
            crontab=crontab,
            enabled=schedule.enabled,
        )
        schedule.periodic_task = pt
        schedule.save(update_fields=["periodic_task"])
        logger.info("Created PeriodicTask %s for schedule %s", pt.name, schedule.id)
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


def remove_schedule(schedule: AutomationSchedule) -> None:
    pt = schedule.periodic_task
    if pt:
        logger.info("Deleting PeriodicTask %s for schedule %s", pt.name, schedule.id)
        schedule.periodic_task = None
        schedule.save(update_fields=["periodic_task"])
        pt.delete()
