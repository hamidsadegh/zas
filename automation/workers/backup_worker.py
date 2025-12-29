from automation.engine.ssh_engine import SSHEngine
from automation.application.connection_service import ConnectionService
from dcim.services.configuration_persistence_service import (
    ConfigurationPersistenceService,
)


def execute_backup(run):
    artifacts = []

    source = "scheduled" if run.job.created_by is None else "manual"
    collected_by = run.job.created_by

    for device in run.devices.all():
        try:
            conn_params = ConnectionService.build_ssh_params(device)
            ssh = SSHEngine(conn_params)

            config = ssh.run_command("show running-config")

            cfg = ConfigurationPersistenceService.persist(
                device=device,
                config_text=config,
                source=source,
                collected_by=collected_by,
                success=True,
            )

            artifacts.append({
                "device_id": str(device.id),
                "hostname": device.name,
                "status": "success",
                "stored": cfg is not None,          # 🔑 new vs unchanged
                "config_id": str(cfg.id) if cfg else None,
            })

        except Exception as exc:
            # IMPORTANT:
            # We record the failure, but we do NOT create a fake configuration.
            ConfigurationPersistenceService.persist(
                device=device,
                config_text="",
                source=source,
                collected_by=collected_by,
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
