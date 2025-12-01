from django.core.validators import RegexValidator
from django.db import models
from dcim.choices import SiteChoices, VLAN_USAGE_CHOICES
import uuid


class VLAN(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cidr_validator = RegexValidator(
        regex=r"^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$",
        message="Enter a valid subnet in CIDR notation (e.g., 10.228.0.0/24)",
    )

    USAGE_CHOICES = VLAN_USAGE_CHOICES

    site = models.CharField(max_length=50, choices=SiteChoices.CHOICES, default="Berlin")
    vlan_id = models.IntegerField()
    name = models.CharField(max_length=100, blank=True, null=True, default="")
    subnet = models.CharField(max_length=50, validators=[cidr_validator], blank=True, null=True)
    gateway = models.GenericIPAddressField(blank=True, null=True)
    usage_area = models.CharField(
        max_length=50, choices=USAGE_CHOICES, null=True, default="Sonstiges"
    )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("site", "vlan_id")
        ordering = ["site", "vlan_id"]

    def __str__(self):
        return f"{self.vlan_id} - {self.name} ({self.site})"