from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

from dcim.models.device import Device
from dcim.models.vlan import VLAN
from dcim.choices import InterfaceStatusChoices, InterfaceKindChoices, InterfaceModeChoices, SwitchportModeChoices



class Interface(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100,
        verbose_name="Interface Name",
        help_text="Name of the interface as reported by the device",
        )
    device = models.ForeignKey(
        Device, 
        on_delete=models.CASCADE, 
        related_name="interfaces"
        )
    mac_address = models.CharField(
        max_length=17, 
        blank=True, 
        null=True,
        verbose_name=_('MAC address'),
        help_text=_("The MAC address of the device's management interface."),
        )
    ip_address = models.GenericIPAddressField(
        protocol="IPv4", 
        blank=True, 
        null=True
        )
    status = models.CharField(
        max_length=20,
        choices=InterfaceStatusChoices.CHOICES,
        default="down",
    )
    endpoint = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name="Endpoint",
        help_text="Connected endpoint (if known)",
        )
    speed = models.PositiveIntegerField(
        blank=True, 
        null=True, 
        verbose_name="Speed (Mbps)",
        help_text="Interface speed in megabits per second",
        )
    duplex = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Duplex mode as reported by the device (e.g., a-full, full, half).",
        )
    speed_mode = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Speed mode as reported by the device (e.g., a-1000, 1000).",
        )
    switchport_enabled = models.BooleanField(
        default=False,
        help_text="Whether this interface operates as a Layer 2 switchport",
        )
    switchport_mode = models.CharField(
        max_length=32,
        choices=SwitchportModeChoices.CHOICES,
        null=True,
        blank=True,
        help_text="Switchport mode as configured on the device",
        )
    access_vlan = models.ForeignKey(
        VLAN,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="access_interfaces",
        )
    native_vlan = models.ForeignKey(
        VLAN,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="native_interfaces",
        )
    vlan_raw = models.CharField(
        max_length=64,
        blank=True,
        help_text="Raw VLAN/switchport value from device output (debug/reference)",
        )
    is_trunk = models.BooleanField(
        default=False,
        help_text="Indicates whether this interface is a trunk port",
        )
    trunk_vlans = models.ManyToManyField(
        VLAN, 
        related_name="trunk_interfaces", 
        blank=True
        )
    is_virtual = models.BooleanField(
        default=False,
        help_text="Indicates whether this interface is virtual (e.g., loopback, VLAN)",
        )
    kind = models.CharField(
        max_length=20,
        choices=InterfaceKindChoices.CHOICES,
        default=InterfaceKindChoices.PHYSICAL,
        db_index=True,
        help_text="Normalized interface type (physical, svi, port-channel, loopback, tunnel)",
        )
    mode = models.CharField(
        max_length=2,
        choices=InterfaceModeChoices.CHOICES,
        null=True,
        blank=True,
        db_index=True,
        help_text="Layer mode (L2 or L3)",
        )
    lag = models.ForeignKey(
        "self", 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name="members",
        verbose_name="LAG",
        help_text="Link Aggregation Group this interface is a member of",
        )
    lag_mode = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="LAG mode (e.g., active, passive, on)",
        )   
    
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.device.name} - {self.name}"
