import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from dcim.models.area import Area
from dcim.models.site import Site
from dcim.models.vendor import Vendor


class InventoryItem(models.Model):
    class ItemType(models.TextChoices):
        DEVICE = "device", _("Device")
        MODULE = "module", _("Module")

    class Status(models.TextChoices):
        IN_STOCK = "in_stock", _("In stock")
        RESERVED = "reserved", _("Reserved")
        INSTALLED = "installed", _("Installed")
        RMA = "rma", _("RMA")
        RETIRED = "retired", _("Retired")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory_number = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        help_text=_("Internal inventory or asset tag number."),
    )
    item_type = models.CharField(
        max_length=16,
        choices=ItemType.choices,
        default=ItemType.DEVICE,
    )
    designation = models.CharField(
        max_length=150,
        help_text=_("General designation such as Switch, Uplink Module, or SFP."),
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_items",
    )
    model = models.CharField(
        max_length=255,
        help_text=_("Vendor model name or free-text model description."),
    )
    serial_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Serial number assigned by the vendor."),
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name="inventory_items",
        help_text=_("Site used for filtering and reporting."),
    )
    area = models.ForeignKey(
        Area,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inventory_items",
        help_text=_("Optional area associated with this inventory item."),
    )
    comment = models.TextField(blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.IN_STOCK,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("Inventory item")
        verbose_name_plural = _("Inventory items")

    def clean(self):
        super().clean()

        errors = {}

        if self.area_id and self.site_id and self.area.site_id != self.site_id:
            errors["area"] = _("Area must belong to the same site as the inventory item.")

        if self.status == self.Status.INSTALLED and not self.comment.strip():
            errors["comment"] = _(
                "Comment is required when an inventory item is marked as installed."
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        label = self.inventory_number or self.serial_number or str(self.id)
        return f"{self.designation} ({label})"
