from django.db import models
import uuid
from dcim.models.area import Area


class Rack(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name="racks")
    height = models.PositiveIntegerField(default=42, help_text="Rack height in U units")
    description = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ("name", "area")
        verbose_name = "Rack"
        verbose_name_plural = "Racks"

    def __str__(self):
        return f"{self.area} / {self.name}"