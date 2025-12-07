# automation/workers/ssh_worker.py

from automation.engine.ssh_engine import SSHEngine


def run_ssh_job(job_run):
    engine = SSHEngine()
    logs = []

    for device in job_run.devices.all():
        try:
            output = engine.run_command(device, "show version")
            logs.append(f"[{device.name}] CLI OK\n{output}")
        except Exception as exc:
            logs.append(f"[{device.name}] CLI FAILED: {exc}")

    return "\n".join(logs)
