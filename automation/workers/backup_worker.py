from automation.engine.ssh_engine import SSHEngine
from automation.application.connection_service import ConnectionService
from dcim.services.configuration_persistence_service import ConfigurationPersistenceService


def execute_backup(run):
    artifacts = []

    for device in run.devices.all():
        try:
            conn_params = ConnectionService.build_ssh_params(device)
            ssh = SSHEngine(conn_params)

            config = ssh.run_command("show running-config")

            # 🔑 THIS WAS MISSING
            ConfigurationPersistenceService.persist(
                device=device,
                config_text=config,
                source="scheduled" if run.job.created_by is None else "manual",
                success=True,
            )

            artifacts.append({
                "device_id": str(device.id),
                "hostname": device.name,
                "status": "success",
            })

        except Exception as exc:
            ConfigurationPersistenceService.persist(
                device=device,
                config_text="",
                source="scheduled",
                success=False,
                error_message=str(exc),
            )

            artifacts.append({
                "device_id": str(device.id),
                "hostname": device.name,
                "status": "failed",
                "error": str(exc),
            })

    return artifacts
