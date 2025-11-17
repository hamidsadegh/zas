import subprocess
from pysnmp.hlapi import *
from devices.models import Device
from django.utils import timezone

class ReachabilityService:
    @staticmethod
    def ping(host: str) -> bool:
        """
        Returns True if host responds to ping.
        """
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
    def snmp_check(host: str, community: str = "public") -> bool:
        """
        Returns True if SNMP responds.
        """
        try:
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=0),
                UdpTransportTarget((host, 161), timeout=1, retries=0),
                ContextData(),
                ObjectType(ObjectIdentity('1.3.6.1.2.1.1.1.0'))  # sysDescr OID
            )
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            return errorIndication is None and errorStatus == 0
        except Exception:
            return False

    @classmethod
    def update_device_status(cls):
        """
        Checks all devices and updates their ping/snmp status.
        """
        devices = Device.objects.all()
        for device in devices:
            reachable_ping = cls.ping(device.management_ip)
            reachable_snmp = False
            if device.device_type:  # only if device supports SNMP
                reachable_snmp = cls.snmp_check(device.management_ip)
            
            device.reachable_ping = reachable_ping
            device.reachable_snmp = reachable_snmp
            device.last_check = timezone.now()
            device.save()
