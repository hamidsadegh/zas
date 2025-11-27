from dcim.models import Device
from automation.models import DeviceTelemetry
from devices.services.snmp_service import SNMPService
from django.utils import timezone

class TelemetryService:
    """Handles telemetry polling and DB persistence."""

    def __init__(self):
        self.snmp = SNMPService()

    def collect(self, device: Device):
        # Example SNMP data collection stub
        stats = self.snmp.get_device_stats(device)
        DeviceTelemetry.objects.create(
            device=device,
            timestamp=timezone.now(),
            cpu_usage=stats.get("cpu"),
            memory_usage=stats.get("memory"),
            uptime=stats.get("uptime"),
            interface_count=stats.get("if_count"),
        )
        return stats
