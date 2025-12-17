# automation/models/automation_job.py

import uuid
from django.db import models
from automation.choices import JobType, JobStatus
from django.conf import settings


class AutomationJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    job_type = models.CharField(
        max_length=30,
        choices=JobType.CHOICES,
    )

    status = models.CharField(
        max_length=20,
        choices=JobStatus.CHOICES,
        default=JobStatus.PENDING,
    )

    description = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="automation_jobs",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        creator = self.created_by.username if self.created_by else "System"
        return f"{self.get_job_type_display()} [{self.status}] by {creator}"

