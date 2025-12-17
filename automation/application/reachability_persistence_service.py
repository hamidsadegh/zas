from django.utils.dateparse import parse_datetime
from django.utils import timezone

from dcim.models import DeviceRuntimeStatus, Device


class ReachabilityPersistenceService:
    @staticmethod
    def persist(payload: dict) -> None:
        checked_at = payload.get("checked_at")
        dt = parse_datetime(checked_at) if checked_at else None
        now = dt or timezone.now()

        for r in payload.get("results", []):
            device_id = r["device_id"]
            statuses = r.get("statuses", {})

            device = Device.objects.get(id=device_id)
            runtime, _ = DeviceRuntimeStatus.objects.get_or_create(device=device)

            # set known fields if present
            if "ping" in statuses:
                runtime.reachable_ping = bool(statuses["ping"])
            if "snmp" in statuses:
                runtime.reachable_snmp = bool(statuses["snmp"])
            if "ssh" in statuses:
                runtime.reachable_ssh = bool(statuses["ssh"])
            if "netconf" in statuses:
                runtime.reachable_netconf = bool(statuses["netconf"])

            runtime.last_check = now
            runtime.save()
