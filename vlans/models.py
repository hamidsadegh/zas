from django.core.validators import RegexValidator
from django.db import models

cidr_validator = RegexValidator(
    regex=r'^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$',
    message="Enter a valid subnet in CIDR notation (e.g., 10.228.0.0/24)"
)



class VLAN(models.Model):
    SITE_CHOICES = [
        ("Berlin", "Berlin"),
        ("Bonn", "Bonn"),
        ("Gemeinsam", "Gemeinsam"),
    ]

    USAGE_CHOICES = [
        ("ACI", "ACI"),
        ("Campus", "Campus"),
        ("Management", "Management"),
        ("PostPro", "PostPro"),
        ("Autark", "Autark"),
        ("BTSU", "BTSU"),
        ("IP-Telefine", "IP-Telefone"),
        ("Frei", "Frei"),
        ("Sonstiges", "Sonstiges"),
    ]

    site = models.CharField(max_length=50, choices=SITE_CHOICES)
    vlan_id = models.IntegerField()
    name = models.CharField(max_length=100, blank=True, null=True, default="")
    subnet = models.CharField(max_length=50, validators=[cidr_validator], null=True)  # accepts 10.228.0.0/24
    gateway = models.GenericIPAddressField(blank=True, null=True)
    usage_area = models.CharField(max_length=50, choices=USAGE_CHOICES, null=True, default="Sonstiges")
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("site", "vlan_id")
        ordering = ["site", "vlan_id"]

    def __str__(self):
        return f"{self.vlan_id} - {self.name} ({self.site})"
