from typing import Dict, Optional

from accounts.services.settings_service import get_snmp_config, get_system_settings


class SNMPEngine:
    """
    Simple SNMP helper that centralizes access to saved SNMP credentials/config.

    This engine is used by TelemetryEngine and can later be extended to do
    real SNMP polling.
    """

    def __init__(self, config: Optional[Dict] = None):
        system_settings = get_system_settings()
        self.config = config or get_snmp_config(system_settings)

    def get_device_stats(self, device) -> Dict:
        """
        Placeholder SNMP polling implementation.

        Returns mock data but ensures the engine has access to the saved config.
        """
        return {
            "cpu": 15.2,
            "memory": 63.7,
            "uptime": 245_120,
            "if_count": 24,
            "snmp_version": self.config.get("version"),
        }
