import uuid
from django.db import models

from ipam.choices import IPAddressStatusChoices, IPAddressRoleChoices
from dcim.models import Interface
from ipaddress import ip_address
from .prefix import Prefix


class IPAddress(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    address = models.GenericIPAddressField()
    prefix = models.ForeignKey(
        Prefix,
        on_delete=models.PROTECT,
        related_name="ip_addresses",
    )
    interface = models.ForeignKey(
        Interface,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ip_addresses",
    )
    status = models.CharField(
        max_length=20,
        choices=IPAddressStatusChoices.choices,
        default=IPAddressStatusChoices.ACTIVE,
    )
    role = models.CharField(
        max_length=20,
        choices=IPAddressRoleChoices.choices,
        default=IPAddressRoleChoices.SECONDARY,
    )
    hostname = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def family(self) -> int:
        """
        IP address family:
        4 = IPv4
        6 = IPv6
        """
        return ip_address(self.address).version

    class Meta:
        ordering = ("address",)

    def clean(self):
        from ipam.services.ipaddress_validation_service import (
            IPAddressValidationService,
        )

        IPAddressValidationService(self).validate()

    def __str__(self):
        return self.address