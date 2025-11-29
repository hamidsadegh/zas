from django.db import models
import uuid
from dcim.models.device import Device
from dcim.models.vlan import VLAN


class Interface(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="interfaces")
    description = models.CharField(max_length=255, blank=True, null=True)
    mac_address = models.CharField(max_length=17, blank=True, null=True)
    ip_address = models.GenericIPAddressField(protocol="IPv4", blank=True, null=True)
    status = models.CharField(
        max_length=20,
        default="down",
        choices=[("up", "Up"), ("down", "Down"), ("disabled", "Disabled")],
    )
    endpoint = models.CharField(max_length=255, blank=True, null=True)
    speed = models.PositiveIntegerField(blank=True, null=True, help_text="Mbps")
    access_vlan = models.ForeignKey(
        VLAN,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="access_interfaces",
    )
    trunk_vlans = models.ManyToManyField(
        VLAN, related_name="trunk_interfaces", blank=True
    )
    is_trunk = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.device.name} - {self.name}"