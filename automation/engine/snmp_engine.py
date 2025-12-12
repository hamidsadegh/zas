from typing import Optional, Dict



class SNMPEngine:
    """
    Low-level SNMP helper engine.
    """

    def check(self, host, config):
        from pysnmp.hlapi import (
            SnmpEngine, CommunityData, UdpTransportTarget, ContextData,
            ObjectType, ObjectIdentity, getCmd
        )
        if not host:
            return False

        version = (config.get("version") or "v2c").lower()
        community = config.get("community", "public")
        port = int(config.get("port") or 161)

        try:
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=1 if version == "v2c" else 0),
                UdpTransportTarget((host, port), timeout=1, retries=0),
                ContextData(),
                ObjectType(ObjectIdentity("1.3.6.1.2.1.1.1.0")),
            )
            error_indication, error_status, _, _ = next(iterator)
            return error_indication is None and error_status == 0

        except Exception:
            return False