from django.db import models
from django.utils import timezone

# Device categories for DeviceType
DEVICE_TYPE_CHOICES = [
    ('ios', 'Cisco IOS Switch'),
    ('iosxe', 'Cisco IOS-XE Switch'),
    ('nxos', 'Cisco NX-OS Switch'),
    ('router', 'Router'),
    ('firewall', 'Firewall'),
    ('ap', 'Access Point'),
    ('server', 'Server'),
    ('other', 'Other'),
]


class Organization(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"

    def __str__(self):
        return self.name


class Area(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children'
    )
    description = models.TextField(blank=True, null=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='areas'
    )

    class Meta:
        unique_together = ('name', 'parent')
        verbose_name_plural = 'Areas'

    def __str__(self):
        full_path = [self.name]
        parent = self.parent
        while parent is not None:
            full_path.append(parent.name)
            parent = parent.parent
        return ' → '.join(full_path[::-1])


class Rack(models.Model):
    name = models.CharField(max_length=100)
    site = models.ForeignKey(Area, on_delete=models.CASCADE, related_name="racks")
    height = models.PositiveIntegerField(default=42, help_text="Rack height in U units")
    description = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ("name", "site")
        verbose_name = "Rack"
        verbose_name_plural = "Racks"

    def __str__(self):
        return f"{self.site} / {self.name}"


class DeviceRole(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Vendor(models.Model):
    name = models.CharField(max_length=100, unique=True)
    website = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class DeviceType(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='device_types')
    model = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=DEVICE_TYPE_CHOICES, default='iosxe')
    description = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('vendor', 'model')

    def __str__(self):
        return f"{self.vendor.name} {self.model}"


class ModuleType(models.Model):
    name = models.CharField(max_length=100)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='modules')
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.vendor.name} {self.name}"


class Device(models.Model):
    # Basic info
    name = models.CharField(max_length=100)
    management_ip = models.GenericIPAddressField(protocol='IPv4', unique=True)
    mac_address = models.CharField(max_length=17, blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    inventory_number = models.CharField(max_length=100, blank=True, null=True)

    # Relations
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='devices')
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True, related_name='devices')
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True, related_name='devices')
    device_type = models.ForeignKey(DeviceType, on_delete=models.SET_NULL, null=True, blank=True, related_name='devices')
    role = models.ForeignKey(DeviceRole, on_delete=models.SET_NULL, null=True, blank=True, related_name='devices')

    # Software / operational
    image_version = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=50, default='unknown', choices=[
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Maintenance'),
        ('unknown', 'Unknown')
    ])

    # Reachability
    reachable_ping = models.BooleanField(default=False)
    reachable_snmp = models.BooleanField(default=False)
    last_check = models.DateTimeField(blank=True, null=True)

    uptime = models.DurationField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.management_ip})"


class DeviceConfiguration(models.Model):
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


class Interface(models.Model):
    name = models.CharField(max_length=100)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='interfaces')
    description = models.CharField(max_length=255, blank=True, null=True)
    mac_address = models.CharField(max_length=17, blank=True, null=True)
    ip_address = models.GenericIPAddressField(protocol='IPv4', blank=True, null=True)
    status = models.CharField(max_length=20, default='down', choices=[
        ('up', 'Up'),
        ('down', 'Down'),
        ('disabled', 'Disabled')
    ])
    endpoint = models.CharField(max_length=255, blank=True, null=True)
    speed = models.PositiveIntegerField(blank=True, null=True, help_text="Mbps")

    def __str__(self):
        return f"{self.device.name} - {self.name}"
