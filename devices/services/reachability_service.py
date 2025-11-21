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
    UsmUserData,
    getCmd,
    usmAesCfb128Protocol,
    usmDESPrivProtocol,
    usmHMACMD5AuthProtocol,
    usmHMACSHAAuthProtocol,
    usmNoAuthProtocol,
    usmNoPrivProtocol,
)

from devices.models import Device
from devices.services.telemetry_service import TelemetryService

AUTH_PROTOCOL_MAP = {
    "md5": usmHMACMD5AuthProtocol,
    "sha": usmHMACSHAAuthProtocol,
}

PRIV_PROTOCOL_MAP = {
    "des": usmDESPrivProtocol,
    "aes128": usmAesCfb128Protocol,
}


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
    def snmp_check(host: Optional[str], config: Optional[dict] = None) -> bool:
        """
        Returns True if SNMP responds using the provided configuration.
        """
        if not host:
            return False

        config = config or {}
        version = (config.get("version") or "v2c").lower()
        port = config.get("port") or 161

        try:
            if version == "v3":
                username = (config.get("username") or "").strip()
                if not username:
                    return False

                security_level = config.get("security_level") or "noAuthNoPriv"
                auth_protocol = AUTH_PROTOCOL_MAP.get(
                    (config.get("auth_protocol") or "").lower(), usmNoAuthProtocol
                )
                priv_protocol = PRIV_PROTOCOL_MAP.get(
                    (config.get("priv_protocol") or "").lower(), usmNoPrivProtocol
                )
                auth_key = (config.get("auth_key") or "").strip() or None
                priv_key = (config.get("priv_key") or "").strip() or None

                if security_level == "noAuthNoPriv":
                    auth_protocol = usmNoAuthProtocol
                    priv_protocol = usmNoPrivProtocol
                    auth_key = None
                    priv_key = None
                elif security_level == "authNoPriv":
                    priv_protocol = usmNoPrivProtocol
                    priv_key = None
                    if not auth_key:
                        return False
                elif security_level == "authPriv":
                    if not auth_key or not priv_key:
                        return False

                auth_data = UsmUserData(
                    username,
                    authKey=auth_key,
                    privKey=priv_key,
                    authProtocol=auth_protocol,
                    privProtocol=priv_protocol,
                )
            else:
                community = (config.get("community") or "public").strip() or "public"
                mp_model = 1 if version == "v2c" else 0
                auth_data = CommunityData(community, mpModel=mp_model)

            iterator = getCmd(
                SnmpEngine(),
                auth_data,
                UdpTransportTarget((host, int(port)), timeout=1, retries=0),
                ContextData(),
                ObjectType(ObjectIdentity("1.3.6.1.2.1.1.1.0")),
            )
            errorIndication, errorStatus, errorIndex, _ = next(iterator)
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
        snmp_config: Optional[dict] = None,
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
                reachable_snmp = cls.snmp_check(device.management_ip, snmp_config)
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
