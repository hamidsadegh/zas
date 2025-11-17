from django.utils import timezone
from devices.services.ssh_service import SSHService
from devices.services.snmp_service import SNMPService
from devices.services.telemetry_service import TelemetryService
from automation.models import JobRun


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

        job_run.log = "\n".join(log_entries)
        job_run.status = "success"

    except Exception as e:
        job_run.log = f"Error: {e}"
        job_run.status = "failed"

    job_run.finished_at = timezone.now()
    job_run.save()
