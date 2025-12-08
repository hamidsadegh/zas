# automation/choices.py

class DevicePlatformChoices:
    """
    Platform identifiers used in Device.platform CharField.
    """
    IOS = "ios"
    IOSXE = "iosxe"
    NXOS = "nxos"
    ASA = "asa"
    JUNOS = "junos"
    EOS = "eos"
    UNKNOWN = "unknown"

    CHOICES = [
        (IOS, "Cisco IOS / IOS-XE"),
        (NXOS, "Cisco NX-OS"),
        (ASA, "Cisco ASA"),
        (JUNOS, "Juniper JunOS"),
        (EOS, "Arista EOS"),
        (UNKNOWN, "Unknown Platform"),
    ]
  

# ---------------------------------------------------------
# Mapping ZAS platform → Netmiko platform identifier
# ---------------------------------------------------------
NETMIKO_PLATFORM_MAP = {
    DevicePlatformChoices.IOS: "cisco_ios",
    DevicePlatformChoices.IOSXE: "cisco_ios",
    DevicePlatformChoices.NXOS: "cisco_nxos",
    DevicePlatformChoices.ASA: "cisco_asa",
    DevicePlatformChoices.EOS: "arista_eos",
    DevicePlatformChoices.JUNOS: "juniper_junos",
    DevicePlatformChoices.UNKNOWN: "autodetect",
}


# ---------------------------------------------------------
# Mapping ZAS platform → backup command
# ---------------------------------------------------------
BACKUP_COMMAND_MAP = {
    DevicePlatformChoices.IOS: "show running-config",
    DevicePlatformChoices.IOSXE: "show running-config",
    DevicePlatformChoices.NXOS: "show running-config",
    DevicePlatformChoices.ASA: "show running-config",
    DevicePlatformChoices.EOS: "show running-config",
    DevicePlatformChoices.JUNOS: "show configuration | display set",
    DevicePlatformChoices.UNKNOWN: "show running-config",  # fallback
}