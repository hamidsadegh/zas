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
