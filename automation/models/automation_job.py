from django.db import models
from django.utils import timezone
import uuid


class AutomationJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    JOB_TYPES = [
        ('backup', 'Configuration Backup'),
        ('ztp', 'Zero Touch Provisioning'),
        ('cli', 'CLI Command Execution'),
        ('telemetry', 'Telemetry Polling'),
        ('reachability', 'Reachability Check'),
    ]
    name = models.CharField(max_length=100)
    job_type = models.CharField(max_length=30, choices=JOB_TYPES)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} ({self.job_type})"
