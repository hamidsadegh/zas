from django.db import models
from encrypted_model_fields.fields import EncryptedCharField
import uuid
from dcim.choices import SITE_CHOICES


class SiteCredential(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.CharField(max_length=50, choices=SITE_CHOICES, unique=True)
    ssh_username = models.CharField(max_length=100)
    ssh_password = EncryptedCharField(max_length=255)
    ssh_port = models.IntegerField(default=22)

    def __str__(self):
        return f"{self.site} credentials"
