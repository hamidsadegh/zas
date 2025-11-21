from django.db import models
from django.utils import timezone
from devices.models import Device


class AutomationJob(models.Model):
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


class JobRun(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    job = models.ForeignKey(AutomationJob, on_delete=models.CASCADE, related_name='runs')
    devices = models.ManyToManyField(Device)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    log = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Run {self.id} of {self.job.name}"


class DeviceTelemetry(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='telemetry')
    timestamp = models.DateTimeField(default=timezone.now)
    cpu_usage = models.FloatField(blank=True, null=True)
    memory_usage = models.FloatField(blank=True, null=True)
    uptime = models.BigIntegerField(blank=True, null=True)
    interface_count = models.IntegerField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.device.name} @ {self.timestamp}"
