import uuid

from django.db import models
from django.utils import timezone

from dcim.models import Device, Interface


class TopologyProtocolChoices(models.TextChoices):
    CDP = "cdp", "CDP"
    LLDP = "lldp", "LLDP"


class TopologyNeighbor(models.Model):
    """
    Observed neighbor fact collected from CDP/LLDP.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="topology_neighbors",
    )
    local_interface = models.ForeignKey(
        Interface,
        on_delete=models.CASCADE,
        related_name="topology_neighbors",
    )
    neighbor_name = models.CharField(max_length=255)
    neighbor_device = models.ForeignKey(
        Device,
        on_delete=models.SET_NULL,
        related_name="reported_neighbors",
        null=True,
        blank=True,
    )
    neighbor_interface = models.CharField(max_length=255, blank=True)
    protocol = models.CharField(max_length=8, choices=TopologyProtocolChoices.choices)
    platform = models.CharField(max_length=100, blank=True)
    capabilities = models.CharField(max_length=255, blank=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["device", "local_interface"]),
            models.Index(fields=["neighbor_name"]),
            models.Index(fields=["protocol"]),
        ]

    def __str__(self) -> str:
        return f"{self.device.name} {self.local_interface.name} -> {self.neighbor_name}"
