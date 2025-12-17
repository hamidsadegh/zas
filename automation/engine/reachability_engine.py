# automation/engine/reachability_engine.py

from typing import Iterable, Optional, List, Tuple, Dict, Any
from django.utils import timezone

from accounts.models import SSHCredential, SNMPCredential
from dcim.models import Device
from .snmp_engine import SNMPEngine
from .netconf_engine import NetconfEngine

import subprocess
import socket
import struct
from contextlib import closing


class ReachabilityEngine:
    """
    Unified engine for ping + SNMP + SSH + NETCONF reachability checks.

    Spine rule:
    - Engine MUST NOT write to DB.
    - It returns measurement results.
    """

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

    @staticmethod
    def ssh_check(host: Optional[str], port: int = 22, timeout: float = 1.0) -> bool:
        if not host:
            return False
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    @staticmethod
    def netconf_check(host: Optional[str]) -> bool:
        if not host:
            return False
        try:
            with closing(socket.create_connection((host, 830), timeout=2.0)):
                return True
        except OSError:
            return False

    def __init__(self):
        self.snmp_engine = SNMPEngine()
        self.netconf_engine = NetconfEngine()

    def measure(
        self,
        *,
        devices: Iterable[Device],
        check_ping=True,
        check_snmp=True,
        check_ssh=False,
        check_netconf=False,
    ) -> Dict[str, Any]:
        """
        Measure reachability. Does NOT persist anything.
        Returns serializable payload.
        """
        now = timezone.now()
        results: List[Dict[str, Any]] = []
        snmp_cache = {}
        ssh_cache = {}

        for device in devices:
            statuses: List[Tuple[str, bool]] = []

            # Ping
            if check_ping:
                val = self.ping(device.management_ip)
                statuses.append(("ping", val))

            # SNMP
            if check_snmp:
                snmp_creds = snmp_cache.get(device.site_id)
                if device.site_id and device.site_id not in snmp_cache:
                    snmp_creds = SNMPCredential.objects.filter(site=device.site).first()
                    snmp_cache[device.site_id] = snmp_creds
                snmp_config = self._build_snmp_config(snmp_creds)
                val = (
                    self.snmp_engine.check(device.management_ip, snmp_config)
                    if snmp_config
                    else False
                )
                statuses.append(("snmp", val))

            # SSH (TCP port check)
            if check_ssh:
                ssh_creds = ssh_cache.get(device.site_id)
                if device.site_id and device.site_id not in ssh_cache:
                    ssh_creds = SSHCredential.objects.filter(site=device.site).first()
                    ssh_cache[device.site_id] = ssh_creds
                port = ssh_creds.ssh_port if ssh_creds else 22
                val = self.ssh_check(device.management_ip, port=port) if device.management_ip else False
                statuses.append(("ssh", val))

            # NETCONF
            if check_netconf:
                val = self.netconf_check(device.management_ip)
                statuses.append(("netconf", val))

            results.append({
                "device_id": str(device.id),
                "hostname": device.name,
                "management_ip": str(device.management_ip) if device.management_ip else None,
                "statuses": {name: bool(ok) for name, ok in statuses},
            })

            summary = {
                "total": len(results),
                "reachable": sum(
                    1 for r in results
                    if r.get("statuses") and all(r["statuses"].values())
                ),
                "unreachable": sum(
                    1 for r in results
                    if not (r.get("statuses") and all(r["statuses"].values()))
                ),
            }


        return {"checked_at": now.isoformat(), "summary": summary, "results": results}

    @staticmethod
    def _build_snmp_config(credential: Optional[SNMPCredential]):
        if not credential:
            return None
        return {
            "version": credential.snmp_version or "v2c",
            "port": credential.snmp_port or 161,
            "community": credential.snmp_community or "public",
            "security_level": credential.snmp_security_level,
            "username": credential.snmp_username,
            "auth_protocol": credential.snmp_auth_protocol,
            "auth_key": credential.snmp_auth_key,
            "priv_protocol": credential.snmp_priv_protocol,
            "priv_key": credential.snmp_priv_key,
        }
