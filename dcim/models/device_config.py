import uuid
from django.db import models
from django.forms import ValidationError
from django.utils import timezone
from django.conf import settings

from dcim.models.device import Device


class DeviceConfiguration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="configs",
    )

    # configuration payload
    config_text = models.TextField()

    # metadata
    collected_at = models.DateTimeField(default=timezone.now)
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="collected_configs",
    )

    source = models.CharField(
        max_length=30,
        choices=[
            ("ssh", "SSH"),
            ("netconf", "NETCONF"),
            ("api", "API"),
            ("import", "Import"),
        ],
        default="ssh",
    )

    # integrity & lineage
    config_hash = models.CharField(max_length=64, db_index=True)
    previous = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="next_versions",
    )

    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-collected_at"]
        indexes = [
            models.Index(fields=["device", "collected_at"]),
        ]
    

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("DeviceConfiguration is immutable")
        super().save(*args, **kwargs)



    def __str__(self):
        return f"{self.device.name} config @ {self.collected_at:%Y-%m-%d %H:%M}"

