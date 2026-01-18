from django.utils.translation import gettext_lazy as _

from utilities.choices import ChoiceSet 


class CliCommandsChoices(ChoiceSet):

    VERSION_CMD = "show version"
    INVENTORY_CMD = "show inventory"
    IF_STATUS_CMD = "show interface status"
    IF_DESC_CMD = "show interface description"
    IF_IP_BRIEF_CMD = "show ip interface brief"
    IF_TRANSCEIVER_CMD = "show interface transceiver"
    PORTCHANNEL_SUMMARY_ISO_CMD = "show etherchannel summary"
    PORTCHANNEL_SUMMARY_NXOS_CMD = "show port-channel summary"
    RUNNING_CONFIG_CMD = "show running-config"
    STACK_SWITCH_CMD = "show switch"

    CHOICES = (
        (VERSION_CMD, _("Version Command")),
        (INVENTORY_CMD, _("Inventory Command")),
        (IF_STATUS_CMD, _("Interface Status Command")),
        (IF_DESC_CMD, _("Interface Description Command")),
        (IF_IP_BRIEF_CMD, _("Interface IP Brief Command")),
        (IF_TRANSCEIVER_CMD, _("Interface Transceiver Command (NX-OS)")),
        (PORTCHANNEL_SUMMARY_ISO_CMD, _("Port-Channel Summary Command (IOS/IOS-XE)")),
        (PORTCHANNEL_SUMMARY_NXOS_CMD, _("Port-Channel Summary Command (NX-OS)")),
        (RUNNING_CONFIG_CMD, _("Running Configuration Command")),
        (STACK_SWITCH_CMD, _("Stack Members Command (IOS/IOS-XE)")),
    )
