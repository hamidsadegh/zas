# automation/engine/reachability_engine.py

from typing import Iterable, Optional, List, Tuple
from django.utils import timezone

from dcim.models import Device, DeviceRuntimeStatus
from .ssh_engine import SSHEngine
from .snmp_engine import SNMPEngine
from .netconf_engine import NetconfEngine

import subprocess
import socket
from contextlib import closing


class ReachabilityEngine:
    """
    Unified engine for ping + SNMP + SSH + NETCONF reachability checks.
    """

    # -------- PING ----------------------------------------------------------
    @staticmethod
    def ping(host: Optional[str]) -> bool:
        if not host:
            return False
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "1", host],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return result.returncode == 0
        except Exception:
            return False

    # -------- SSH -----------------------------------------------------------
    @staticmethod
    def ssh_check(host: Optional[str]) -> bool:
        if not host:
            return False
        try:
            with closing(socket.create_connection((host, 22), timeout=2.0)):
                return True
        except OSError:
            return False

    # -------- NETCONF -------------------------------------------------------
    @staticmethod
    def netconf_check(host: Optional[str]) -> bool:
        if not host:
            return False
        try:
            with closing(socket.create_connection((host, 830), timeout=2.0)):
                return True
        except OSError:
            return False

    # -------- SNMP ----------------------------------------------------------
    def __init__(self):
        self.snmp_engine = SNMPEngine()
        self.netconf_engine = NetconfEngine()

    # -------- MAIN AGGREGATION ---------------------------------------------
    def update_device_status(
        self,
        *,
        devices: Iterable[Device],
        check_ping=True,
        check_snmp=True,
        check_ssh=False,
        check_netconf=False,
        snmp_config=None,
    ) -> List[dict]:

        now = timezone.now()
        results = []

        for device in devices:
            statuses: List[Tuple[str, bool]] = []
            runtime, _ = DeviceRuntimeStatus.objects.get_or_create(device=device)

            # Ping
            if check_ping:
                val = self.ping(device.management_ip)
                runtime.reachable_ping = val
                statuses.append(("ping", val))

            # SNMP
            if check_snmp:
                val = self.snmp_engine.check(device.management_ip, snmp_config or {})
                runtime.reachable_snmp = val
                statuses.append(("snmp", val))

            # SSH
            if check_ssh:
                val = self.ssh_check(device.management_ip)
                runtime.reachable_ssh = val
                statuses.append(("ssh", val))

            # NETCONF
            if check_netconf:
                val = self.netconf_check(device.management_ip)
                runtime.reachable_netconf = val
                statuses.append(("netconf", val))

            runtime.last_check = now
            runtime.save(update_fields=[
                "reachable_ping",
                "reachable_snmp",
                "reachable_ssh",
                "reachable_netconf",
                "last_check",
                "updated_at",
            ])

            results.append({"device": device, "statuses": statuses})

        return results
