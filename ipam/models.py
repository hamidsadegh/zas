from django.db import models

from dcim.models import Device, Interface, VLAN
from dcim.choices import SITE_CHOICES

class Prefix(models.Model):
    prefix = models.CharField(max_length=50)  # 10.0.0.0/24
    site = models.CharField(max_length=50, choices=SITE_CHOICES)
    vlan = models.ForeignKey(VLAN, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.prefix} ({self.site})"


class IPAddress(models.Model):
    address = models.GenericIPAddressField()
    device = models.ForeignKey(Device, null=True, blank=True, on_delete=models.SET_NULL)
    interface = models.ForeignKey(
        Interface, null=True, blank=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        return self.address
