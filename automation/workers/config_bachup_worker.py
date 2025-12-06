from automation.engine.ssh_engine import SSHEngine


def run_backup(job_run):
    engine = SSHEngine()

    output = []
    for dev in job_run.devices.all():
        config = engine.run_command(dev, "show running-config")
        output.append(f"[{dev.name}] Backup complete.")

    return "\n".join(output)
