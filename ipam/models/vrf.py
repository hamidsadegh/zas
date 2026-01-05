import uuid
from django.db import models

from dcim.models import Site


class VRF(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name="vrfs",
        )
    rd = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name="Route Distinguisher",
        help_text="Route Distinguisher for the VRF",
        )
    description = models.TextField(blank=True, null=True)   
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("site", "name")
        ordering = ("site__name", "name")

    def __str__(self):
        site_name = self.site.name if self.site else "-"
        return f"{self.name} ({site_name})"