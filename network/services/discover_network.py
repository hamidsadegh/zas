import ipaddress
from types import SimpleNamespace
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

from dcim.models import Site, Device, DeviceRuntimeStatus
from network.models.discovery import (
    DiscoveryRange,
    DiscoveryCandidate,
    DiscoveryFilter,
)
from network.services.discovery_scanner import DiscoveryScanner
from network.services.discovery_filtering import hostname_passes_filters


class NetworkDiscoveryService:
    """
    Nightly discovery workflow.

    Discovery is observational:
    - exact match  -> update runtime status only
    - mismatch     -> mark candidate as mismatch
    - new device   -> create discovery candidate only
    """

    def __init__(self, *, site: Site):
        self.site = site
        self.scanner = DiscoveryScanner()
        self.now = timezone.now()
        self.filters = list(
            DiscoveryFilter.objects.filter(site=self.site, enabled=True)
        )

    # -------------------------------------------------
    # Public API
    # -------------------------------------------------

    def run(self, cidr_override: str | None = None) -> dict:
        ranges = self._get_ranges(cidr_override)

        alive = 0
        for dr in ranges:
            alive += self._scan_range(dr)

        exact, mismatch, new = self._classify()

        return {
            "ranges": len(ranges),
            "alive": alive,
            "exact": exact,
            "mismatch": mismatch,
            "new": new,
        }

    # -------------------------------------------------
    # Discovery ranges
    # -------------------------------------------------

    def _get_ranges(self, cidr_override: str | None = None):
        if cidr_override:
            return [
                SimpleNamespace(
                    cidr=cidr_override,
                    scan_method="tcp",
                    scan_port=22,
                )
            ]
        return DiscoveryRange.objects.filter(
            site=self.site,
            enabled=True,
        )

    # -------------------------------------------------
    # Stage 1: scan + store candidates
    # -------------------------------------------------

    @transaction.atomic
    def _scan_range(self, dr) -> int:
        try:
            ips = [
                str(ip)
                for ip in ipaddress.ip_network(dr.cidr, strict=False).hosts()
            ]
        except ValueError:
            return 0

        if dr.scan_method == "icmp":
            results = self.scanner.scan_icmp(ips)
        else:
            results = self.scanner.scan_tcp(ips, dr.scan_port)

        alive = 0

        for r in results:
            if not r.alive:
                continue

            if not hostname_passes_filters(r.hostname, self.filters):
                continue

            alive += 1

            DiscoveryCandidate.objects.update_or_create(
                site=self.site,
                ip_address=r.ip,
                defaults={
                    "hostname": (r.hostname or "").lower(),
                    "alive": True,
                    "reachable_ping": r.method == "icmp",
                    "reachable_ssh": r.method == "tcp",
                    "last_seen": self.now,
                },
            )

        return alive

    # -------------------------------------------------
    # Stage 2: classification (NO topology mutation)
    # -------------------------------------------------

    @transaction.atomic
    def _classify(self) -> tuple[int, int, int]:
        exact = mismatch = new = 0

        candidates = DiscoveryCandidate.objects.filter(
            site=self.site,
            classified=False,
        )

        for c in candidates:
            hostname = (c.hostname or "").lower()

            device_by_ip = Device.objects.filter(
                site=self.site,
                management_ip=c.ip_address,
            ).first()

            device_by_name = Device.objects.filter(
                site=self.site,
                name__iexact=hostname,
            ).first()

            # -------------------------------
            # Case A: exact match
            # -------------------------------
            if device_by_ip and device_by_name and device_by_ip.id == device_by_name.id:
                self._update_runtime_status(device_by_ip, c)
                c.classified = True
                c.accepted = True
                c.save(update_fields=["classified", "accepted"])
                exact += 1
                continue

            # -------------------------------
            # Case B: mismatch
            # -------------------------------
            if device_by_ip or device_by_name:
                c.classified = True
                c.accepted = False  # mismatch
                c.save(update_fields=["classified", "accepted"])
                mismatch += 1
                continue

            # -------------------------------
            # Case C: new device
            # -------------------------------
            c.classified = False  # keep as unclassified until manual/auto assignment
            c.accepted = None  # pending review
            c.save(update_fields=["classified", "accepted"])
            new += 1

        return exact, mismatch, new

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    def _update_runtime_status(self, device: Device, candidate: DiscoveryCandidate):
        status, _ = DeviceRuntimeStatus.objects.get_or_create(device=device)
        status.reachable_ping |= candidate.reachable_ping
        status.reachable_ssh |= candidate.reachable_ssh
        status.last_check = candidate.last_seen
        status.save()
