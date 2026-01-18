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
from typing import Optional, Iterable

__all__ = (
    "Device",
    "DeviceType",
    "DeviceRole",
    "DeviceModule",
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
        max_length=100,
        verbose_name=_('model'),
        help_text=_('Model name as assigned by the vendor.'),
        )
    platform = models.CharField(
        max_length=50,
        choices=DevicePlatformChoices.CHOICES,
        default=DevicePlatformChoices.UNKNOWN,
        verbose_name=_("platform"),
        help_text=_("Operating system / platform family (e.g. IOS-XE, NX-OS, Junos)."),
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.PROTECT,
        related_name="device_type",
        verbose_name=_("vendor"),
        help_text=_("Manufacturer of this device model."),
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
    front_svg = models.FileField(
        upload_to="device-type-svg",
        blank=True,
        null=True,
        help_text="Auto-generated flat front SVG for rack elevations.",
    )
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name=_('weight'),
        help_text=_('Weight of the device with default power supply in kilograms.'),
        )
    dimensions = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('dimensions'),
        help_text=_('Physical dimensions (L x W x H) in standard units, e.g. inches or mm.')
        )
    default_ac_power_supply_watts = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_('default AC power supply (watts)'),
        help_text=_('Default power capacity of a single AC power supply for this device type.'),
        )
    switching_capacity_gbps = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name=_('switching capacity (Gbps)'),
        help_text=_('Total switching capacity of the device in gigabits per second.'),
        )
    forwarding_rate_mpps = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name=_('forwarding rate (Mpps)'),
        help_text=_('Packet forwarding rate in millions of packets per second.'),
        )
    datasheet = models.URLField(
        blank=True,
        null=True,
        verbose_name=_('datasheet'),
        help_text=_('URL to the manufacturer\'s datasheet for this device type.'),
        )
    clone_fields = (
        'vendor', 'platform', 'u_height', 'is_full_depth', 'airflow', 'weight',
        )


    class Meta:
        unique_together = ("vendor", "model")

    def __str__(self):
        vendor = self.vendor.name if self.vendor else "Unknown Vendor"
        return f"{vendor} {self.model}"
    

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
        unique=True,
        verbose_name=_("name"),
        help_text=_("Unique name identifying this device."),
    )
    management_ip = models.GenericIPAddressField(
        protocol="IPv4", 
        unique=True,
        verbose_name=_('management IP address'),
        help_text=_("The primary IP address used to manage this device."),
        )
    mac_address = models.CharField(
        max_length=17, 
        blank=True, 
        null=True,
        verbose_name=_('MAC address'),
        help_text=_("The MAC address of the device's management interface."),
        )
    serial_number = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name=_('serial number'),
        help_text=_("Chassis serial number, assigned by the vendor."),
        )
    inventory_number = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=_('inventory number'),
        help_text=_("An internal inventory or asset tag number."),
        )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name="devices",
        help_text=_(
            "Optional labels used for grouping, filtering, and automation "
            "(e.g. 'reachability_check_tag', 'datacenter', 'production')."
        ),
    )

    # Relations
    device_type = models.ForeignKey(
        DeviceType, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True, 
        related_name="devices",
        help_text=_("The specific model of this device."),
        )
    role = models.ForeignKey(
        DeviceRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="devices",
        help_text=_(
            "Functional role of the device in the network "
            "(e.g. core, access, firewall, spine, leaf)."
        ),
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name="devices",
        help_text=_("Site where this device is installed."),
    )
    area = models.ForeignKey(
        Area,
        on_delete=models.PROTECT,
        related_name="devices",
        help_text=_("Set once the device is physically installed."),
    )
    rack = models.ForeignKey(
        Rack,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="devices",
        help_text=_("Rack where the device is mounted (optional)."),
    )
    is_stacked = models.BooleanField(
        default=False,
        verbose_name=_('is stacked'),
        help_text=_('Indicates whether this device is part of a stack or chassis.'),
        )
    position = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(RACK_U_HEIGHT_MAX + 0.5)],
        verbose_name=_('position (U)'),
        help_text=_('The lowest-numbered unit occupied by the device'),
        )
    face = models.CharField(
        max_length=5,
        blank=True,
        null=True,
        choices=DeviceFaceChoices.CHOICES,
        verbose_name=_('rack face'),
        )
    airflow = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=DeviceAirflowChoices.CHOICES,
        verbose_name=_('airflow'),
        )
    # Software / operational
    image_version = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name=_('image version'),
        help_text=_("The operating system version running on the device."),
        )
    status = models.CharField(
        max_length=50,
        choices=DeviceStatusChoices,
        default="unknown",
    )
    source = models.CharField(
        max_length=32,
        choices=[
            ("manual", "Manual"),
            ("discovery", "Discovery"),
            ("import", "Import"),
        ],
        default="manual",
        db_index=True,
    )
    last_seen = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time this device was observed by discovery or polling",
    )
    uptime = models.DurationField(
        blank=True, 
        null=True,
        verbose_name=_('uptime'),
        help_text=_('Total time the device has been operational since last reboot.'),
        )
    last_reboot = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name=_('last reboot'),
        help_text=_('Timestamp of the device\'s last reboot.'),
        )
        
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        label = self.name or str(self.management_ip)
        return label

    def clean(self):
        super().clean()
        if self.area and self.area.site_id != self.site_id:
            raise ValidationError(
                {"area": "Area must belong to the same site as the device."}
        )
        if self.rack and self.rack.area_id != self.area_id:
            raise ValidationError(
                {"rack": "Rack must belong to the same area as the device."}
            )
        if self.rack and self.position is not None:
            occupied = Device.objects.filter(
                rack=self.rack, position=self.position
            ).exclude(pk=self.pk).exists()
            if occupied:
                raise ValidationError(
                    {"position": _("This rack unit is already occupied in the selected rack.")}
                )
        if self.device_type and not self.device_type.platform:
            raise ValidationError(
                {"device_type": "Device type must define a platform for automation."}
            )
    
    def save(self, *args, **kwargs):
        previous_rack_id = None
        if self.pk:
            previous_rack_id = Device.objects.filter(pk=self.pk).values_list("rack_id", flat=True).first()
        super().save(*args, **kwargs)
        racks_to_update = {previous_rack_id, self.rack_id}
        for rack_id in [r for r in racks_to_update if r]:
            update_rack_occupied_units(rack_id)

    def delete(self, *args, **kwargs):
        rack_id = self.rack_id
        super().delete(*args, **kwargs)
        if rack_id:
            update_rack_occupied_units(rack_id)


class DeviceModule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="modules")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    vendor = models.ForeignKey(
        Vendor, on_delete=models.SET_NULL, blank=True, null=True, related_name="modules"
    )
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    class Meta:
        verbose_name = "Device Module"
        verbose_name_plural = "Device Modules"

    @property
    def serial_number_display(self):
        if not self.serial_number:
            return None
        serial = self.serial_number.strip()
        if not serial:
            return None
        serial_upper = serial.upper()
        if serial_upper in ("N/A", "UNKNOWN", "N") or serial_upper.startswith("UNKNOWN:"):
            return None
        return serial

    def __str__(self):
        serial = self.serial_number_display
        if serial:
            return f"{self.device.name} - {self.name} ({serial})"
        return f"{self.device.name} - {self.name}"
    
    
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


def update_rack_occupied_units(rack_id: Optional[uuid.UUID]):
    """
    Recompute and persist the set of occupied rack units for a given rack.
    Stored as a list of numeric positions to keep the Rack.occupied_units field in sync.
    """
    if not rack_id:
        return
    positions: Iterable = (
        Device.objects.filter(rack_id=rack_id)
        .exclude(position__isnull=True)
        .values_list("position", flat=True)
    )
    Rack.objects.filter(id=rack_id).update(
        occupied_units=[float(pos) for pos in positions]
    )
