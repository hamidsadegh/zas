from django.utils import timezone

from dcim.models import Device
from automation.models import DeviceTelemetry
from automation.engine.snmp_engine import SNMPEngine


class NetconfEngine:
    """
    Telemetry polling + persistence.

    Currently uses SNMPEngine as a backend and writes to DeviceTelemetry.
    """

    def __init__(self, snmp_engine: SNMPEngine | None = None):
        self.snmp_engine = snmp_engine or SNMPEngine()

    def collect(self, device: Device) -> dict:
        """
        Collect telemetry for a device and save a DeviceTelemetry record.

        Returns the collected stats dictionary.
        """
        stats = self.snmp_engine.get_device_stats(device)

        DeviceTelemetry.objects.create(
            device=device,
            timestamp=timezone.now(),
            cpu_usage=stats.get("cpu"),
            memory_usage=stats.get("memory"),
            uptime=stats.get("uptime"),
            interface_count=stats.get("if_count"),
        )

        return stats

