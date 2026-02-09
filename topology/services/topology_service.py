from django.utils import timezone

from dcim.models import Device, Interface
from dcim.services.hostname_utils import normalize_hostname
from topology.models import TopologyNeighbor


class TopologyService:
    """
    Upsert topology neighbor observations.
    """

    @staticmethod
    def upsert_neighbor(
        *,
        device: Device,
        local_interface: Interface,
        neighbor_name: str,
        neighbor_interface: str,
        protocol: str,
        platform: str = "",
        capabilities: str = "",
    ) -> TopologyNeighbor:
        neighbor_name = normalize_hostname(neighbor_name, site=device.site)
        if not neighbor_name or not local_interface:
            raise ValueError("neighbor_name and local_interface are required")

        neighbor_device = Device.objects.filter(name__iexact=neighbor_name).first()
        now = timezone.now()

        neighbor, _ = TopologyNeighbor.objects.update_or_create(
            device=device,
            local_interface=local_interface,
            protocol=protocol,
            neighbor_name=neighbor_name,
            neighbor_interface=neighbor_interface or "",
            defaults={
                "neighbor_device": neighbor_device,
                "platform": platform or "",
                "capabilities": capabilities or "",
                "last_seen": now,
            },
        )
        return neighbor
