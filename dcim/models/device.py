from django.db import models
from dcim.models.organization import Organization
from dcim.choices import DEVICE_STATUS_CHOICES
from dcim.choices import SITE_CHOICES
from dcim.choices import DEVICE_TYPE_CHOICES
from dcim.models.vendor import Vendor
from dcim.models.device import Device   
from django.utils import timezone
from dcim.models.area import Area
from dcim.models.rack import Rack
import uuid



class DeviceType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="device_types")
    model = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=DEVICE_TYPE_CHOICES, default="iosxe")
    description = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ("vendor", "model")

    def __str__(self):
        return f"{self.vendor.name} {self.model}"

class DeviceRole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    

class DeviceConfiguration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.OneToOneField(
        Device, on_delete=models.CASCADE, related_name="configuration"
    )
    config_text = models.TextField(help_text="Full configuration text")
    last_updated = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Device Configuration"
        verbose_name_plural = "Device Configurations"

    def __str__(self):
        return f"Configuration for {self.device.name}"


class DeviceModule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="modules")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    vendor = models.ForeignKey(
        Vendor, on_delete=models.SET_NULL, blank=True, null=True, related_name="modules"
    )
    serial_number = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Device Module"
        verbose_name_plural = "Device Modules"

    def __str__(self):
        return f"{self.device.name} - {self.name} ({self.serial_number})"
    
    
class Device(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic info
    name = models.CharField(max_length=100)
    management_ip = models.GenericIPAddressField(protocol="IPv4", unique=True)
    mac_address = models.CharField(max_length=17, blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    inventory_number = models.CharField(max_length=100, blank=True, null=True)

    # Relations
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="devices"
    )
    area = models.ForeignKey(
        Area, on_delete=models.SET_NULL, null=True, blank=True, related_name="devices"
    )
    vendor = models.ForeignKey(
        Vendor, on_delete=models.SET_NULL, null=True, blank=True, related_name="devices"
    )
    device_type = models.ForeignKey(
        DeviceType, on_delete=models.SET_NULL, null=True, blank=True, related_name="devices"
    )
    role = models.ForeignKey(
        DeviceRole, on_delete=models.SET_NULL, null=True, blank=True, related_name="devices"
    )
    rack = models.ForeignKey(
        Rack, on_delete=models.SET_NULL, null=True, blank=True, related_name="devices"
    )
    site = models.CharField(max_length=50, choices=SITE_CHOICES, default="Gemeinsam")

    # Software / operational
    image_version = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(
        max_length=50,
        default="unknown",
        choices=DEVICE_STATUS_CHOICES,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.management_ip})"
    
    
class DeviceRuntimeStatus(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.OneToOneField(
        Device, on_delete=models.CASCADE, related_name="runtime"
    )
    reachable_ping = models.BooleanField(default=False)
    reachable_snmp = models.BooleanField(default=False)
    reachable_ssh = models.BooleanField(default=False)
    reachable_netconf = models.BooleanField(default=False)
    last_check = models.DateTimeField(null=True, blank=True)
    uptime = models.DurationField(null=True, blank=True)

    def __str__(self):
        return f"Runtime status for {self.device.name}"
