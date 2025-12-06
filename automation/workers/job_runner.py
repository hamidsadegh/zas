from datetime import timedelta

from django.utils import timezone

from automation.models import JobRun
from dcim.models import Device
from automation.engine.reachability_engine import ReachabilityEngine
from automation.engine.ssh_engine import SSHEngine
from automation.engine.netconf_engine import NetconfEngine
from accounts.services.settings_service import (
    get_reachability_checks,
    get_snmp_config,
    get_system_settings,
    update_reachability_last_run,
)


def execute_job(job_run: JobRun, snmp_config=None, reachability_checks=None, system_settings=None):
    job = job_run.job
    job_run.status = "running"
    job_run.started_at = timezone.now()
    job_run.save()

    try:
        log_entries = []

        if job.job_type == "cli":
            ssh = SSHEngine()
            for device in job_run.devices.all():
                output = ssh.run_command(device, "show version")
                log_entries.append(f"[{device.name}] CLI:\n{output}\n")

        elif job.job_type == "backup":
            ssh = SSHEngine()
            for device in job_run.devices.all():
                output = ssh.run_command(device, "show running-config")
                log_entries.append(f"[{device.name}] Backup done.\n")

        elif job.job_type == "netconf":
            netconf = NetconfEngine()
            for device in job_run.devices.all():
                netconf.collect(device)
                log_entries.append(f"[{device.name}] Netconf collected.\n")
                
        elif job.job_type == "reachability":
            settings = system_settings or get_system_settings()
            checks = reachability_checks or get_reachability_checks(settings)
            snmp_config = snmp_config or get_snmp_config(settings)
            enabled_checks = [name for name, enabled in checks.items() if enabled]

            if not enabled_checks:
                log_entries.append("Reachability job skipped: all probes disabled in System Settings.")
            else:
                now = timezone.now()
                interval = timedelta(minutes=getattr(settings, "reachability_interval_minutes", 1) or 1)
                if getattr(settings, "reachability_last_run", None) and (
                    now - settings.reachability_last_run
                ) < interval:
                    remaining = interval - (now - settings.reachability_last_run)
                    log_entries.append(
                        f"Reachability job skipped: waiting {remaining} before next run."
                    )
                else:
                    devices = job_run.devices.all()
                    if not devices.exists():
                        devices = Device.objects.all()

                    results = ReachabilityEngine.update_device_status(
                        devices=devices,
                        check_ping=checks["ping"],
                        check_snmp=checks["snmp"],
                        check_ssh=checks["ssh"],
                        check_netconf=checks.get("netconf"),
                        snmp_config=snmp_config,
                    )

                    if not results:
                        log_entries.append("Reachability executed but no devices were updated.")
                    else:
                        for entry in results:
                            status_chunks = [
                                f"{name.upper()}: {'OK' if state else 'FAIL'}"
                                for name, state in entry["statuses"]
                            ]
                            log_entries.append(f"[{entry['device'].name}] {', '.join(status_chunks)}")

                    update_reachability_last_run(settings, now)

        job_run.log = "\n".join(log_entries)
        job_run.status = "success"

    except Exception as e:
        job_run.log = f"Error: {e}"
        job_run.status = "failed"

    job_run.finished_at = timezone.now()
    job_run.save()
