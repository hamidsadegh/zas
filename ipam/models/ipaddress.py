import uuid
from ipaddress import ip_address

from django.db import models
from django.core.validators import RegexValidator

from ipam.choices import IPAddressStatusChoices, IPAddressRoleChoices
from dcim.models import Interface
from ipam.models.prefix import Prefix


MAC_VALIDATOR = RegexValidator(
    regex=r"^([0-9A-Fa-f]{2}:){5}([0-9A-Fa-f]{2})$",
    message="MAC address must be in format AA:BB:CC:DD:EE:FF",
)


class IPAddress(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Core addressing
    address = models.GenericIPAddressField(
        verbose_name="IP address",
        help_text="IPv4 or IPv6 address",
        )
    prefix = models.ForeignKey(
        Prefix,
        on_delete=models.PROTECT,
        related_name="ip_addresses",
        help_text="Prefix this IP address belongs to",
        )
    interface = models.ForeignKey(
        Interface,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ip_addresses",
        help_text="Interface this IP is assigned to",
        )
    # Semantics
    status = models.CharField(
        max_length=20,
        choices=IPAddressStatusChoices.choices,
        default=IPAddressStatusChoices.ACTIVE,
        help_text="Operational status of the IP address",
        )
    role = models.CharField(
        max_length=20,
        choices=IPAddressRoleChoices.choices,
        default=IPAddressRoleChoices.SECONDARY,
        help_text="Functional role of the IP address",
        )
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary IP address on the interface",
        )
    is_reserved = models.BooleanField(
        default=False,
        help_text="Reserved IP (not assignable automatically)",
        )
    # Naming / L2 hinting
    hostname = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="DNS hostname associated with this IP",
        )
    mac_address = models.CharField(
        max_length=17,
        blank=True,
        null=True,
        validators=[MAC_VALIDATOR],
        help_text="Associated MAC address (if applicable)",
        )
    # Metadata
    last_seen = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Last time this IP was observed by automation",
        )

    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("address",)
        constraints = [
            models.UniqueConstraint(
                fields=["address", "prefix"],
                name="uniq_ip_per_prefix",
            ),
        ]

    @property
    def family(self) -> int:
        """
        IP address family:
        4 = IPv4
        6 = IPv6
        """
        return ip_address(self.address).version

    def clean(self):
        from ipam.services.ipaddress_validation_service import (
            IPAddressValidationService,
        )

        IPAddressValidationService(self).validate()

    def __str__(self):
        return f"{self.address}"
