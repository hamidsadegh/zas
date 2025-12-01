from typing import Dict

from accounts.models.system_settings import SystemSettings


def get_system_settings() -> SystemSettings:
    """Return the singleton SystemSettings instance."""
    obj, _ = SystemSettings.objects.get_or_create(pk=1)
    return obj


def get_section_fields(section: str):
    mapping = {
        "tacacs": SystemSettings.TACACS_FIELDS,
        "reachability": SystemSettings.REACHABILITY_FIELDS + SystemSettings.SNMP_FIELDS,
        "snmp": SystemSettings.SNMP_FIELDS,
        "other": SystemSettings.OTHER_FIELDS,
    }
    return mapping.get(section, ())


def get_reachability_checks(settings: SystemSettings) -> Dict[str, bool]:
    return {
        "ping": settings.reachability_ping_enabled,
        "snmp": settings.reachability_snmp_enabled,
        "ssh": settings.reachability_ssh_enabled,
        "netconf": settings.reachability_netconf_enabled,
    }


def get_snmp_config(settings: SystemSettings) -> Dict[str, str]:
    return {
        "version": settings.snmp_version or "v2c",
        "port": settings.snmp_port or 161,
        "community": (settings.snmp_community or "public").strip() or "public",
        "security_level": settings.snmp_security_level or "noAuthNoPriv",
        "username": (settings.snmp_username or "").strip(),
        "auth_protocol": settings.snmp_auth_protocol or "",
        "auth_key": settings.snmp_auth_key or "",
        "priv_protocol": settings.snmp_priv_protocol or "",
        "priv_key": settings.snmp_priv_key or "",
    }


def update_reachability_last_run(settings: SystemSettings, timestamp):
    settings.reachability_last_run = timestamp
    settings.save(update_fields=["reachability_last_run"])
