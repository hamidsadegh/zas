from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

from dcim.choices import *
from dcim.constants import *
from dcim.fields import *
from django.utils import timezone
from dcim.models.area import Area
from dcim.models.rack import Rack
from dcim.models.vendor import Vendor
from dcim.models.site import Site
from dcim.models.tag import Tag
import uuid

__all__ = (
    "Device",
    "DeviceType",
    "DeviceRole",
    "DeviceModule",
    "DevicePlatform",
    "DeviceRuntimeStatus",
)


#
# Device Types
#

class DeviceType(models.Model):
    """ 
    A device type represents a specific model of network device from a given vendor. 
    """
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
        )
    model = models.CharField(
        verbose_name=_('model'),
        max_length=100
        )
    vendor = models.ForeignKey(
        Vendor, 
        on_delete=models.CASCADE, 
        related_name="device_types"
        )
    description = models.TextField(
        blank=True, 
        null=True
        ,verbose_name=_('description')
        )
    part_number = models.CharField(
        verbose_name=_('part number'),
        max_length=50,
        blank=True,
        help_text=_('Discrete part number (optional)')
        )
    u_height = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=1.0,
        verbose_name=_('height (U)')
        )
    exclude_from_utilization = models.BooleanField(
        default=False,
        verbose_name=_('exclude from utilization'),
        help_text=_('Devices of this type are excluded when calculating rack utilization.')
        )
    is_full_depth = models.BooleanField(
        default=True,
        verbose_name=_('is full depth'),
        help_text=_('Device consumes both front and rear rack faces.')
        )
    subdevice_role = models.CharField(
        max_length=50,
        choices=SubdeviceRoleChoices,
        blank=True,
        null=True,
        verbose_name=_('parent/child status'),
        help_text=_('Parent devices house child devices in device bays. Leave blank '
                    'if this device type is neither a parent nor a child.')
        )
    airflow = models.CharField(
        verbose_name=_('airflow'),
        max_length=50,
        choices=DeviceAirflowChoices,
        blank=True,
        null=True
        )
    front_image = models.ImageField(
        upload_to='devicetype-images',
        blank=True
        )
    rear_image = models.ImageField(
        upload_to='devicetype-images',
        blank=True
        )
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name=_('weight')
        )
    clone_fields = (
        'vendor', 'default_platform', 'u_height', 'is_full_depth', 'airflow', 'weight',
        )

    class Meta:
        unique_together = ("vendor", "model")

    def __str__(self):
        return f"{self.vendor.name} {self.model}"
    

class DeviceRole(models.Model):
    """ 
    A device role represents the functional role of a network device within the infrastructure, such as core router, access switch, or firewall.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Device(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic info
    name = models.CharField(
        max_length=100,
        verbose_name=_('name'),
        blank=True,
        null=True,
        help_text=_("A unique name identifying this device within the organization.")
        )
    management_ip = models.GenericIPAddressField(
        verbose_name=_('management IP address'),
        protocol="IPv4", 
        unique=True,
        help_text=_("The primary IP address used to manage this device.")
        )
    mac_address = models.CharField(
        max_length=17, 
        blank=True, 
        null=True,
        verbose_name=_('MAC address'),
        help_text=_("The MAC address of the device's management interface.")
        )
    serial_number = models.CharField(
        verbose_name=_('serial number'),
        max_length=50, 
        blank=True, 
        null=True,
        help_text=_("Chassis serial number, assigned by the vendor.")
        )
    inventory_number = models.CharField(
        verbose_name=_('inventory number'),
        max_length=100, 
        blank=True, 
        null=True,
        help_text=_("An internal inventory or asset tag number.")
        )
    tags = models.ManyToManyField(
        Tag, 
        related_name="devices", 
        blank=True
        )

    # Relations
    area = models.ForeignKey(
        Area, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="devices"
        )
    vendor = models.ForeignKey(
        Vendor, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="devices"
        )
    device_type = models.ForeignKey(
        DeviceType, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True, 
        related_name="devices"
        )
    role = models.ForeignKey(
        DeviceRole, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="devices"
        )
    rack = models.ForeignKey(
        Rack, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="devices"
        )
    is_stacked = models.BooleanField(
        default=False,
        verbose_name=_('is stacked'),
        help_text=_('Indicates whether this device is part of a stack or chassis.')
        )
    position = models.DecimalField(
        verbose_name=_('position (U)'),
        max_digits=4,
        decimal_places=1,
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(RACK_U_HEIGHT_MAX + 0.5)],
        help_text=_('The lowest-numbered unit occupied by the device')
        )
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name="devices",
        help_text=_("Site where this device is installed."),
    )
    face = models.CharField(
        max_length=5,
        verbose_name=_('rack face'),
        choices=DeviceFaceChoices.CHOICES,
        blank=True,
        null=True,
        )
    platform = models.CharField(
        max_length=100, 
        choices= DevicePlatformChoices.CHOICES, 
        blank=True, 
        null=True, 
        default="unknown"
        )
    airflow = models.CharField(
        verbose_name=_('airflow'),
        max_length=50,
        choices=DeviceAirflowChoices.CHOICES,
        blank=True,
        null=True
        )

    # Software / operational
    image_version = models.CharField(
        verbose_name=_('image version'),
        max_length=100, 
        blank=True, 
        null=True,
        )
    status = models.CharField(
        max_length=50,
        default="unknown",
        choices=DeviceStatusChoices,
    )
    uptime = models.DurationField(
        blank=True, 
        null=True,
        verbose_name=_('uptime'),
        help_text=_('Total time the device has been operational since last reboot.')
        )
    last_reboot = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name=_('last reboot'),
        help_text=_('Timestamp of the device\'s last reboot.')
        )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.management_ip})"


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

    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = "Device Runtime Status"
        verbose_name_plural = "Device Runtime Statuses"

    def __str__(self):
        return f"Runtime status for {self.device.name}"
