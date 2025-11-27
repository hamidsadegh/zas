from typing import Dict, Optional

from accounts.services.settings_service import get_snmp_config, get_system_settings


class SNMPService:
    """Simple SNMP helper that centralizes access to saved credentials."""

    def __init__(self, config: Optional[Dict] = None):
        system_settings = get_system_settings()
        self.config = config or get_snmp_config(system_settings)

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
