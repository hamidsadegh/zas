import uuid
from django.db import models
from django.utils import timezone

from dcim.models.device import Device


class DeviceConfiguration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="configs")
    backup_time = models.DateTimeField(default=timezone.now)
    config_text = models.TextField()
    source = models.CharField(max_length=30, default="ssh")
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-backup_time"]

    def __str__(self):
        return f"{self.device.name} @ {self.backup_time}"
