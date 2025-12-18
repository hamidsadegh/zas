import uuid
from django.db import models
from django.db.models import Q

from ipam.choices import PrefixStatusChoices, PrefixRoleChoices
from dcim.models import Site, VLAN
from .vrf import VRF


class Prefix(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cidr = models.CharField(max_length=50)
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name="prefixes",
    )
    vrf = models.ForeignKey(
        VRF,
        on_delete=models.PROTECT,
        related_name="prefixes",
        null=True,
        blank=True,
    )
    vlan = models.ForeignKey(
        VLAN,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="prefixes",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    status = models.CharField(
        max_length=20,
        choices=PrefixStatusChoices.choices,
        default=PrefixStatusChoices.ACTIVE,
    )
    role = models.CharField(
        max_length=20,
        choices=PrefixRoleChoices.choices,
        default=PrefixRoleChoices.USER,
    )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cidr", "site"],
                condition=Q(vrf__isnull=True),
                name="unique_prefix_cidr_site_no_vrf",
            ),
            models.UniqueConstraint(
                fields=["cidr", "site", "vrf"],
                name="unique_prefix_cidr_site_vrf",
            ),
        ]
        ordering = ("site__name", "cidr")

    def clean(self):
        from ipam.services.prefix_validation_service import PrefixValidationService

        PrefixValidationService(self).validate()

    def __str__(self):
        site_name = self.site.name if self.site else "-"
        vrf_name = self.vrf.name if self.vrf else "default"
        return f"{self.cidr} ({site_name} / {vrf_name})"