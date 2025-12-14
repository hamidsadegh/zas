import uuid
from django.db import models


class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    color = models.CharField(
        max_length=7,
        default="#888888",
        help_text="Optional UI color for tag badges (e.g., #FF5500)",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
