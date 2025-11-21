from datetime import timedelta

from django.utils import timezone

from accounts.models import SystemSettings
from automation.models import JobRun
from devices.models import Device
from devices.services.reachability_service import ReachabilityService
from devices.services.ssh_service import SSHService
from devices.services.telemetry_service import TelemetryService


def execute_job(job_run: JobRun):
    job = job_run.job
    job_run.status = "running"
    job_run.started_at = timezone.now()
    job_run.save()

    try:
        log_entries = []

        if job.job_type == "cli":
            ssh = SSHService()
            for device in job_run.devices.all():
                output = ssh.run_command(device, "show version")
                log_entries.append(f"[{device.name}] CLI:\n{output}\n")

        elif job.job_type == "backup":
            ssh = SSHService()
            for device in job_run.devices.all():
                output = ssh.run_command(device, "show running-config")
                log_entries.append(f"[{device.name}] Backup done.\n")

        elif job.job_type == "telemetry":
            telemetry = TelemetryService()
            for device in job_run.devices.all():
                telemetry.collect(device)
                log_entries.append(f"[{device.name}] Telemetry collected.\n")
        elif job.job_type == "reachability":
            settings = SystemSettings.get()
            checks = settings.get_reachability_checks()
            enabled_checks = [name for name, enabled in checks.items() if enabled]

            if not enabled_checks:
                log_entries.append("Reachability job skipped: all probes disabled in System Settings.")
            else:
                now = timezone.now()
                interval = timedelta(minutes=settings.reachability_interval_minutes or 1)
                if settings.reachability_last_run and (now - settings.reachability_last_run) < interval:
                    remaining = interval - (now - settings.reachability_last_run)
                    log_entries.append(
                        f"Reachability job skipped: waiting {remaining} before next run."
                    )
                else:
                    devices = job_run.devices.all()
                    if not devices.exists():
                        devices = Device.objects.all()

                    results = ReachabilityService.update_device_status(
                        devices=devices,
                        check_ping=checks["ping"],
                        check_snmp=checks["snmp"],
                        check_ssh=checks["ssh"],
                        check_telemetry=checks["telemetry"],
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

                    settings.reachability_last_run = now
                    settings.save(update_fields=["reachability_last_run"])

        job_run.log = "\n".join(log_entries)
        job_run.status = "success"

    except Exception as e:
        job_run.log = f"Error: {e}"
        job_run.status = "failed"

    job_run.finished_at = timezone.now()
    job_run.save()
