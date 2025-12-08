# automation/backup_tasks/config_backup.py

import logging
from celery import shared_task
from django.utils import timezone

from dcim.models import Device
from dcim.models.device_config import DeviceConfiguration
from automation.engine.ssh_engine import SSHEngine
from automation.choices import BACKUP_COMMAND_MAP, DevicePlatformChoices


logger = logging.getLogger(__name__)


@shared_task
def backup_device_config(device_id: str):
    """
    Executes a configuration backup of a single device.
    Creates a DeviceConfiguration history entry.
    """
    try:
        device = Device.objects.get(id=device_id)
    except Device.DoesNotExist:
        logger.error(f"Config backup: device {device_id} does not exist.")
        return "device_not_found"

    # Determine Netmiko platform string
    platform = getattr(device, "platform", DevicePlatformChoices.UNKNOWN)
    command = BACKUP_COMMAND_MAP.get(platform)

    if not command:
        msg = f"No backup command defined for platform '{platform}'"
        logger.error(msg)
        DeviceConfiguration.objects.create(
            device=device,
            backup_time=timezone.now(),
            config_text="",
            success=False,
            error_message=msg,
        )
        return "no_command"

    ssh = SSHEngine(device)

    try:
        config_text = ssh.run_command(command)

        DeviceConfiguration.objects.create(
            device=device,
            backup_time=timezone.now(),
            config_text=config_text,
            success=True,
            error_message=None,
        )

        logger.info(f"Backup OK: {device.name}")
        return "ok"

    except Exception as exc:
        DeviceConfiguration.objects.create(
            device=device,
            backup_time=timezone.now(),
            config_text="",
            success=False,
            error_message=str(exc),
        )

        logger.error(f"Backup FAILED: {device.name}: {exc}")
        return "failed"
