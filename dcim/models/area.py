import uuid

from django.core.exceptions import ValidationError
from django.db import models

from dcim.models.site import Site


class Area(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100,
        help_text="Name of the area. It can be hierarchical by specifying a parent area. From Global/Continent/Country/City/Building/Floor/Room",
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name="areas",
        help_text="Site that contains this area.",
    )
    description = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ("site", "name", "parent")
        verbose_name_plural = "Areas"

    def __str__(self):
        full_path = [self.name]
        parent = self.parent
        while parent is not None:
            full_path.append(parent.name)
            parent = parent.parent
        path = " → ".join(full_path[::-1])
        return f"{self.site.name} / {path}" if self.site else path

    def clean(self):
        super().clean()
        if self.parent and self.site_id and self.parent.site_id != self.site_id:
            raise ValidationError(
                {"parent": "Parent area must belong to the same site as this area."}
            )
