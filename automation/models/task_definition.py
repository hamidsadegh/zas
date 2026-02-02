import uuid
from django.db import models


class AutomationTaskDefinition(models.Model):
    class Category(models.TextChoices):
        AUTOMATION = "automation", "Automation"
        NETWORK = "network", "Network"
        SYSTEM = "system", "System"

    class ManagedBy(models.TextChoices):
        UI = "ui", "Automation UI"
        SYSTEM = "system", "System Settings"
        WORKFLOW = "workflow", "Workflow / UI"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=120)
    task_name = models.CharField(max_length=200, unique=True)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.AUTOMATION,
    )
    description = models.TextField(blank=True)
    managed_by = models.CharField(
        max_length=20,
        choices=ManagedBy.choices,
        default=ManagedBy.UI,
    )
    supports_schedule = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.task_name})"
