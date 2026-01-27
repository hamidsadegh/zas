import uuid
from django.conf import settings
from django.db import models
from dcim.models.site import Site


class DiscoveryRange(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name="discovery_ranges",
    )

    cidr = models.CharField(max_length=64)
    enabled = models.BooleanField(default=True)

    # semantics
    description = models.CharField(max_length=255, blank=True)

    # behavior
    scan_method = models.CharField(
        max_length=10,
        choices=(("tcp", "TCP"), ("icmp", "ICMP")),
        default="tcp",
    )
    scan_port = models.PositiveIntegerField(default=22)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("site", "cidr")

    def __str__(self):
        return f"{self.site.name} – {self.cidr}"
    

class DiscoveryFilter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name="discovery_filters",
    )

    # positive match: hostname MUST contain ALL of these (comma-separated)
    hostname_contains = models.CharField(
        max_length=255,
        blank=True,
        help_text="Comma-separated substrings that must be present in hostname",
    )

    # negative match: hostname MUST NOT contain ANY of these (comma-separated)
    hostname_not_contains = models.CharField(
        max_length=255,
        blank=True,
        help_text="Comma-separated substrings that must NOT be present in hostname",
    )

    enabled = models.BooleanField(default=True)

    description = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["site", "id"]

    def __str__(self):
        parts = []
        if self.hostname_contains:
            parts.append(f"+[{self.hostname_contains}]")
        if self.hostname_not_contains:
            parts.append(f"-[{self.hostname_not_contains}]")
        rule = " ".join(parts) if parts else "no-op"
        return f"{self.site.name}: {rule}"
    

class DiscoveryCandidate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    site = models.ForeignKey(Site, on_delete=models.CASCADE)

    ip_address = models.GenericIPAddressField()
    hostname = models.CharField(max_length=255, blank=True)

    alive = models.BooleanField(default=False)
    reachable_ssh = models.BooleanField(default=False)
    reachable_ping = models.BooleanField(default=False)

    last_seen = models.DateTimeField()

    classified = models.BooleanField(default=False)
    accepted = models.BooleanField(null=True)  # None = not reviewed

    class Meta:
        unique_together = ("site", "ip_address")


class AutoAssignJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auto_assign_jobs",
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auto_assign_jobs",
    )
    candidate_hostname = models.CharField(max_length=255, blank=True)
    limit = models.PositiveIntegerField(null=True, blank=True)
    include_config = models.BooleanField(default=True)
    candidate_ids = models.JSONField(default=list, blank=True)
    total_candidates = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    failure_count = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Auto-assign {self.id}"


class AutoAssignJobItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(
        AutoAssignJob,
        on_delete=models.CASCADE,
        related_name="items",
    )
    candidate = models.ForeignKey(
        DiscoveryCandidate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auto_assign_items",
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auto_assign_items",
    )
    hostname = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    success = models.BooleanField(default=False)
    device = models.ForeignKey(
        "dcim.Device",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auto_assign_items",
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        label = self.hostname or str(self.ip_address) if self.ip_address else "candidate"
        return f"{label} ({'ok' if self.success else 'failed'})"
