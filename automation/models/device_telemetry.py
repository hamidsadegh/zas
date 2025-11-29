from django.db import models
from django.utils import timezone
from dcim.models import Device


class DeviceTelemetry(models.Model):
    # Telemetry data will later move to TSDB (Influx/Victoria/Prometheus)
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
