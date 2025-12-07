import uuid
from django.db import models
from django.utils import timezone

from dcim.models import Device
from .automation_job import AutomationJob


class JobRun(models.Model):
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    job = models.ForeignKey(AutomationJob, on_delete=models.CASCADE, related_name='runs')
    devices = models.ManyToManyField(Device, related_name="job_runs")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    params = models.JSONField(null=True, blank=True)     # input parameters
    result = models.JSONField(null=True, blank=True)     # output structured result
    log = models.TextField(blank=True, null=True)        # text log

    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def duration(self):
        if self.started_at and self.finished_at:
            return self.finished_at - self.started_at
        return None

    def __str__(self):
        return f"Run of {self.job.name} @ {self.created_at:%Y-%m-%d %H:%M}"

