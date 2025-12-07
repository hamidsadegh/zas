# automation/workers/backup_worker.py

from automation.engine.ssh_engine import SSHEngine


def run_backup_job(job_run):
    """
    Executes a configuration backup via SSH.
    """
    engine = SSHEngine()
    logs = []

    for device in job_run.devices.all():
        try:
            engine.run_command(device, "show running-config")
            logs.append(f"[{device.name}] backup done.")
        except Exception as exc:
            logs.append(f"[{device.name}] backup failed: {exc}")

    return "\n".join(logs)

