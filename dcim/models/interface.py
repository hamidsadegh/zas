from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

from dcim.models.device import Device
from dcim.models.vlan import VLAN
from dcim.choices import InterfaceStatusChoices



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
    access_vlan = models.ForeignKey(
        VLAN,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="access_interfaces",
        )
    trunk_vlans = models.ManyToManyField(
        VLAN, 
        related_name="trunk_interfaces", 
        blank=True
        )
    is_trunk = models.BooleanField(
        default=False,
        help_text="Indicates whether this interface is a trunk port",
        )
    is_virtual = models.BooleanField(
        default=False,
        help_text="Indicates whether this interface is virtual (e.g., loopback, VLAN)",
        )
    
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.device.name} - {self.name}"