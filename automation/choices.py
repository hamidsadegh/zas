# automation/choices.py

from dcim.choices import DevicePlatformChoices

# ---------------------------------------------------------
# Mapping DeviceType.platform → Netmiko driver
# ---------------------------------------------------------
NETMIKO_PLATFORM_MAP = {
    DevicePlatformChoices.IOS: "cisco_ios",
    DevicePlatformChoices.IOS_XE: "cisco_ios",
    DevicePlatformChoices.NX_OS: "cisco_nxos",
    DevicePlatformChoices.FIREWALL: "cisco_asa",
    DevicePlatformChoices.EOS: "arista_eos",
    DevicePlatformChoices.UNKNOWN: "autodetect",
}

# ---------------------------------------------------------
# Mapping DeviceType.platform → backup command
# ---------------------------------------------------------
BACKUP_COMMAND_MAP = {
    DevicePlatformChoices.IOS: "show running-config",
    DevicePlatformChoices.IOS_XE: "show running-config",
    DevicePlatformChoices.NX_OS: "show running-config",
    DevicePlatformChoices.FIREWALL: "show running-config",
    DevicePlatformChoices.EOS: "show running-config",
    DevicePlatformChoices.UNKNOWN: "show running-config",
}

# ---------------------------------------------------------
# Types of Jobs for automation
# ---------------------------------------------------------
class JobType:
    CONFIG_BACKUP = "config_backup"
    REACHABILITY = "reachability"
    TELEMETRY = "telemetry"
    COMMAND = "command"

    CHOICES = (
        (CONFIG_BACKUP, "Configuration Backup"),
        (REACHABILITY, "Reachability Check"),
        (TELEMETRY, "Telemetry Snapshot"),
        (COMMAND, "Run Command"),
    )


# ---------------------------------------------------------
# Status of Jobs for automation
# ---------------------------------------------------------
class JobStatus:
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

    CHOICES = (
        (PENDING, "Pending"),
        (QUEUED, "Queued"),
        (RUNNING, "Running"),
        (SUCCESS, "Success"),
        (FAILED, "Failed"),
    )
