# automation/tasks.py

# Import all modules that define @shared_task
from automation.scheduler import check_devices_reachability, schedule_configuration_backups
from automation.backup_tasks.config_backup import backup_device_config

__all__ = [
    "check_devices_reachability",
    "schedule_configuration_backups",
    "backup_device_config",
]
