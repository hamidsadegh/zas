# automation/models/schedule.py

import uuid
from django.db import models
from django_celery_beat.models import PeriodicTask


class AutomationSchedule(models.Model):
    class ScheduleType(models.TextChoices):
        INTERVAL = "interval", "Interval"
        CRONTAB = "crontab", "Crontab"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(
        max_length=100,
        help_text="Human-readable name for this schedule (e.g. 'Reachability Poller').",
    )
    task_name = models.CharField(
        max_length=200,
        help_text="Fully-qualified Celery task path (e.g. 'automation.scheduler.check_devices_reachability').",
    )

    enabled = models.BooleanField(default=True)

    schedule_type = models.CharField(
        max_length=20,
        choices=ScheduleType.choices,
        default=ScheduleType.INTERVAL,
    )

    # Interval schedule (seconds)
    interval_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Interval in seconds (used when schedule_type=interval).",
    )

    # Crontab schedule
    minute = models.CharField(max_length=64, default="*")
    hour = models.CharField(max_length=64, default="*")
    day_of_week = models.CharField(max_length=64, default="*")
    day_of_month = models.CharField(max_length=64, default="*")
    month_of_year = models.CharField(max_length=64, default="*")

    periodic_task = models.OneToOneField(
        PeriodicTask,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="automation_schedule",
        help_text="Linked django-celery-beat PeriodicTask.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("name", "task_name")

    def __str__(self):
        return f"{self.name} ({self.task_name})"

    @property
    def cron_expression(self) -> str:
        if self.schedule_type != self.ScheduleType.CRONTAB:
            return "-"
        return f"{self.minute} {self.hour} {self.day_of_month} {self.month_of_year} {self.day_of_week}"

    @property
    def schedule_summary(self) -> str:
        if self.schedule_type == self.ScheduleType.INTERVAL:
            return f"every {self.interval_seconds}s" if self.interval_seconds else "invalid interval"
        return self.cron_expression
