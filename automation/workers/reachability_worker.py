
from datetime import timedelta
from django.utils import timezone

from automation.engine.reachability_engine import ReachabilityEngine
from dcim.models import Device
from accounts.services.settings_service import update_reachability_last_run


def run_reachability_job(job_run, snmp_config, reachability_checks, system_settings):
    """
    Executes reachability verification (ping, snmp, ssh, netconf)
    for the devices in JobRun.
    """

    enabled_checks = [name for name, enabled in reachability_checks.items() if enabled]
    if not enabled_checks:
        return "Reachability skipped: all probes disabled."

    devices = job_run.devices.all()
    if not devices.exists():
        devices = Device.objects.all()

    engine = ReachabilityEngine()

    results = engine.update_device_status(
        devices=devices,
        check_ping=reachability_checks.get("ping"),
        check_snmp=reachability_checks.get("snmp"),
        check_ssh=reachability_checks.get("ssh"),
        check_netconf=reachability_checks.get("netconf"),
        snmp_config=snmp_config,
    )

    # Format log messages
    log_lines = []
    for entry in results:
        status_str = ", ".join(
            f"{name.upper()}: {'OK' if result else 'FAIL'}"
            for name, result in entry["statuses"]
        )
        log_lines.append(f"[{entry['device'].name}] {status_str}")

    # Update last run timestamp
    update_reachability_last_run(system_settings, timezone.now())

    return "\n".join(log_lines) if log_lines else "Reachability executed but no devices were updated."
