from typing import Dict, Optional

from accounts.models import SystemSettings


class SNMPService:
    """Simple SNMP helper that centralizes access to saved credentials."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or SystemSettings.get().get_snmp_config()

    def get_device_stats(self, device):
        # Placeholder for actual SNMP polling. Returns mock data but ensures
        # the service has access to the saved configuration.
        return {
            "cpu": 15.2,
            "memory": 63.7,
            "uptime": 245120,
            "if_count": 24,
            "snmp_version": self.config.get("version"),
        }
