from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("network", "0002_auto_assign_job"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DiscoveryScanJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("scan_kind", models.CharField(choices=[("all", "All ranges"), ("single", "Single IP"), ("cidr", "CIDR"), ("range", "Range")], default="all", max_length=16)),
                ("scan_method", models.CharField(choices=[("tcp", "TCP"), ("icmp", "ICMP")], default="tcp", max_length=10)),
                ("scan_port", models.PositiveIntegerField(default=22)),
                ("scan_params", models.JSONField(blank=True, default=dict)),
                ("total_ranges", models.PositiveIntegerField(default=0)),
                ("processed_ranges", models.PositiveIntegerField(default=0)),
                ("alive_count", models.PositiveIntegerField(default=0)),
                ("exact_count", models.PositiveIntegerField(default=0)),
                ("mismatch_count", models.PositiveIntegerField(default=0)),
                ("new_count", models.PositiveIntegerField(default=0)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed")], default="pending", max_length=16)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="discovery_scan_jobs", to=settings.AUTH_USER_MODEL)),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="discovery_scan_jobs", to="dcim.site")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
