import logging
import re
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from dcim.choices import DevicePlatformChoices
from dcim.models import Device, Interface
from network.adapters.netmiko import NetmikoAdapter
from network.adapters.topology import parse_cdp_neighbors, parse_lldp_neighbors
from topology.models import TopologyNeighbor
from topology.services.topology_service import TopologyService

logger = logging.getLogger(__name__)

ELIGIBLE_PLATFORMS = {
    DevicePlatformChoices.IOS,
    DevicePlatformChoices.IOS_XE,
    DevicePlatformChoices.NX_OS,
    DevicePlatformChoices.ROUTER,
}


def get_eligible_devices():
    return Device.objects.select_related("device_type").filter(
        device_type__platform__in=ELIGIBLE_PLATFORMS,
    )


def _normalize_interface_name(name: str) -> str:
    if not name:
        return ""
    value = name.strip()
    replacements = {
        r"^Port-channel": "Po",
        r"^GigabitEthernet": "Gi",
        r"^Gig": "Gi",
        r"^TenGigabitEthernet": "Te",
        r"^FortyGigabitEthernet": "Fo",
        r"^TwentyFiveGigE": "Tw",
        r"^HundredGigE": "Hu",
        r"^Ethernet": "Eth",
    }
    for pattern, short in replacements.items():
        value = re.sub(pattern, short, value, flags=re.IGNORECASE)
    value = re.sub(r"^(Gi|Te|Fo|Po|Hu|Tw|Eth)\s+", r"\1", value, flags=re.IGNORECASE)
    return value


def _resolve_local_interface(device: Device, raw_name: str):
    candidates = [raw_name]
    normalized = _normalize_interface_name(raw_name)
    if normalized:
        candidates.append(normalized)
    compact = re.sub(r"\s+", "", raw_name)
    if compact and compact not in candidates:
        candidates.append(compact)
    compact_normalized = _normalize_interface_name(compact)
    if compact_normalized and compact_normalized not in candidates:
        candidates.append(compact_normalized)

    for candidate in candidates:
        if not candidate:
            continue
        iface = Interface.objects.filter(device=device, name__iexact=candidate).first()
        if iface:
            return iface
    return None


def collect_neighbors_for_device(device: Device) -> bool:
    try:
        with NetmikoAdapter(device) as adapter:
            cdp_raw = adapter.run_command_raw("show cdp neighbors detail")["raw"]
            if not cdp_raw or "% Invalid" in cdp_raw or "Invalid input" in cdp_raw:
                cdp_raw = adapter.run_command_raw("show cdp neighbors")["raw"]
            lldp_raw = adapter.run_command_raw("show lldp neighbors detail")["raw"]
            if not lldp_raw or "% Invalid" in lldp_raw or "Invalid input" in lldp_raw:
                lldp_raw = adapter.run_command_raw("show lldp neighbors")["raw"]

        for entry in parse_cdp_neighbors(cdp_raw):
            local_interface = _resolve_local_interface(device, entry["local_interface"])
            if not local_interface:
                logger.info(
                    "Topology skip: %s missing local interface %s",
                    device.name,
                    entry["local_interface"],
                )
                continue
            TopologyService.upsert_neighbor(
                device=device,
                local_interface=local_interface,
                neighbor_name=entry["neighbor_name"],
                neighbor_interface=entry["neighbor_interface"],
                protocol=entry["protocol"],
                platform=entry["platform"],
                capabilities=entry["capabilities"],
            )

        for entry in parse_lldp_neighbors(lldp_raw):
            local_interface = _resolve_local_interface(device, entry["local_interface"])
            if not local_interface:
                logger.info(
                    "Topology skip: %s missing local interface %s",
                    device.name,
                    entry["local_interface"],
                )
                continue
            TopologyService.upsert_neighbor(
                device=device,
                local_interface=local_interface,
                neighbor_name=entry["neighbor_name"],
                neighbor_interface=entry["neighbor_interface"],
                protocol=entry["protocol"],
                platform=entry["platform"],
                capabilities=entry["capabilities"],
            )
        return True
    except Exception as exc:
        logger.warning("Topology collection failed for %s: %s", device.name, exc)
        return False


@shared_task(bind=True)
def collect_topology_neighbors(self, device_id=None):
    devices = get_eligible_devices()
    if device_id:
        devices = devices.filter(id=device_id)

    results = {"success": 0, "failed": 0}

    for device in devices:
        if collect_neighbors_for_device(device):
            results["success"] += 1
        else:
            results["failed"] += 1

    return results


@shared_task
def cleanup_topology_neighbors(days: int = 30):
    cutoff = timezone.now() - timedelta(days=days)
    stale = TopologyNeighbor.objects.filter(last_seen__lt=cutoff)
    count = stale.count()
    stale.delete()
    return count
