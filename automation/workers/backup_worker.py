from automation.engine.ssh_engine import SSHEngine
from automation.application.connection_service import ConnectionService


def execute_backup(run):
    artifacts = []

    for device in run.devices.all():
        conn_params = ConnectionService.build_ssh_params(device)
        ssh = SSHEngine(conn_params)

        config = ssh.run_command("show running-config")

        artifacts.append({
            "device_id": str(device.id),
            "hostname": device.name,
            "config": config,
        })

    return artifacts
