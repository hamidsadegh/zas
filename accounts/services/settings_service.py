from typing import Dict

from accounts.models.system_settings import SystemSettings


def get_system_settings() -> SystemSettings:
    """Return the singleton SystemSettings instance."""
    return SystemSettings.objects.load()


def get_section_fields(section: str):
    mapping = {
        "tacacs": SystemSettings.TACACS_FIELDS,
        "reachability": SystemSettings.REACHABILITY_FIELDS,
        "superusers": SystemSettings.ALLOW_LOCAL_SUPERUSERS,
    }
    return mapping.get(section, ())


def get_reachability_checks(settings: SystemSettings) -> Dict[str, bool]:
    return {
        "ping": settings.reachability_ping_enabled,
        "snmp": settings.reachability_snmp_enabled,
        "ssh": settings.reachability_ssh_enabled,
        "netconf": settings.reachability_netconf_enabled,
    }

def update_reachability_last_run(settings: SystemSettings, timestamp):
    settings.reachability_last_run = timestamp
    settings.save(update_fields=["reachability_last_run"])
