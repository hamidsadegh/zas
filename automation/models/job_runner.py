from django.db import models
from django.utils import timezone
import uuid
from .automation_job import AutomationJob
from dcim.models import Device


class JobRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    job = models.ForeignKey(AutomationJob, on_delete=models.CASCADE, related_name='runs')
    devices = models.ManyToManyField(Device)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    params = models.JSONField(null=True, blank=True)
    result = models.JSONField(null=True, blank=True)
    log = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Run {self.id} of {self.job.name}"
