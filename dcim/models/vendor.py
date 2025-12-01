from django.db import models
import uuid


class Vendor(models.Model):
    """
    A vendor represents a manufacturer or supplier of network devices; for example, Cisco, Juniper, or Arista.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    website = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
