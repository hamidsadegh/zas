import uuid

from django.db import models
from encrypted_model_fields.fields import EncryptedCharField

from dcim.models import Site


class SiteCredential(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.OneToOneField(
        Site,
        on_delete=models.CASCADE,
        related_name="credentials",
    )
    ssh_username = models.CharField(max_length=100)
    ssh_password = EncryptedCharField(max_length=255)
    ssh_port = models.IntegerField(default=22)

    def __str__(self):
        site_name = self.site.name if getattr(self, "site", None) else "Unassigned"
        return f"{site_name} credentials"
