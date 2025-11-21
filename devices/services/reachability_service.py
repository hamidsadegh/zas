import socket
import subprocess
from contextlib import closing
from typing import Iterable, List, Optional, Tuple

from django.utils import timezone
from pysnmp.hlapi import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    getCmd,
)

from devices.models import Device
from devices.services.telemetry_service import TelemetryService


class ReachabilityService:
    @staticmethod
    def ping(host: Optional[str]) -> bool:
        """
        Returns True if host responds to ping.
        """
        if not host:
            return False
        try:
            output = subprocess.run(
                ["ping", "-c", "1", "-W", "1", host],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return output.returncode == 0
        except Exception:
            return False

    @staticmethod
    def snmp_check(host: Optional[str], community: str = "public") -> bool:
        """
        Returns True if SNMP responds.
        """
        if not host:
            return False
        try:
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=0),
                UdpTransportTarget((host, 161), timeout=1, retries=0),
                ContextData(),
                ObjectType(ObjectIdentity("1.3.6.1.2.1.1.1.0")),
            )
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            return errorIndication is None and errorStatus == 0
        except Exception:
            return False

    @staticmethod
    def ssh_check(host: Optional[str], port: int = 22, timeout: float = 2.0) -> bool:
        if not host:
            return False
        try:
            with closing(socket.create_connection((host, port), timeout=timeout)):
                return True
        except OSError:
            return False

    @staticmethod
    def telemetry_check(device: Device, telemetry_service: TelemetryService) -> bool:
        try:
            telemetry_service.collect(device)
            return True
        except Exception:
            return False

    @classmethod
    def update_device_status(
        cls,
        *,
        devices: Optional[Iterable[Device]] = None,
        check_ping: bool = True,
        check_snmp: bool = True,
        check_ssh: bool = False,
        check_telemetry: bool = False,
        snmp_community: str = "public",
    ) -> List[dict]:
        """
        Checks the provided devices and updates their reachability flags.

        Returns a list of per-device status dictionaries for logging.
        """
        device_qs = devices or Device.objects.all()
        telemetry_service = TelemetryService() if check_telemetry else None
        now = timezone.now()
        results: List[dict] = []

        for device in device_qs:
            statuses: List[Tuple[str, bool]] = []
            update_fields: List[str] = []

            if check_ping:
                reachable_ping = cls.ping(device.management_ip)
                device.reachable_ping = reachable_ping
                statuses.append(("ping", reachable_ping))
                update_fields.append("reachable_ping")

            if check_snmp:
                reachable_snmp = cls.snmp_check(device.management_ip, snmp_community)
                device.reachable_snmp = reachable_snmp
                statuses.append(("snmp", reachable_snmp))
                update_fields.append("reachable_snmp")

            if check_ssh:
                reachable_ssh = cls.ssh_check(device.management_ip)
                device.reachable_ssh = reachable_ssh
                statuses.append(("ssh", reachable_ssh))
                update_fields.append("reachable_ssh")

            if check_telemetry and telemetry_service:
                reachable_telemetry = cls.telemetry_check(device, telemetry_service)
                device.reachable_telemetry = reachable_telemetry
                statuses.append(("telemetry", reachable_telemetry))
                update_fields.append("reachable_telemetry")

            if update_fields:
                device.last_check = now
                update_fields.append("last_check")
                device.save(update_fields=update_fields)

            if statuses:
                results.append({"device": device, "statuses": statuses})

        return results
