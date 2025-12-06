import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from dcim.models.organization import Organization


class Site(models.Model):
    """
    Logical location that belongs to an organization and contains one or more areas.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="sites",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("organization", "name")
        ordering = ("organization__name", "name")
        verbose_name = _("Site")
        verbose_name_plural = _("Sites")

    def __str__(self):
        return f"{self.organization.name} / {self.name}"
