import uuid
from django.db import models

from dcim.models import Device
from automation.choices import JobStatus
from .automation_job import AutomationJob


class JobRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    job = models.ForeignKey(
        AutomationJob,
        on_delete=models.CASCADE,
        related_name="runs",
    )

    devices = models.ManyToManyField(
        Device,
        related_name="job_runs",
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=JobStatus.CHOICES,
        default=JobStatus.PENDING,
        db_index=True,
    )

    params = models.JSONField(null=True, blank=True)
    result = models.JSONField(null=True, blank=True)
    log = models.TextField(blank=True, null=True)

    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def duration(self):
        if self.started_at and self.finished_at:
            return self.finished_at - self.started_at
        return None

    @property
    def creator_label(self):
        return self.job.created_by.username if self.job.created_by else "System"

    def __str__(self):
        return (
            f"{self.job.get_job_type_display()} run "
            f"[{self.status}] by {self.creator_label} "
            f"@ {self.created_at:%Y-%m-%d %H:%M}"
        )
