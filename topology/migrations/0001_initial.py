import uuid

from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("dcim", "0018_devicestackmember"),
    ]

    operations = [
        migrations.CreateModel(
            name="TopologyNeighbor",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("neighbor_name", models.CharField(max_length=255)),
                ("neighbor_interface", models.CharField(max_length=255, blank=True)),
                ("protocol", models.CharField(choices=[("cdp", "CDP"), ("lldp", "LLDP")], max_length=8)),
                ("platform", models.CharField(max_length=100, blank=True)),
                ("capabilities", models.CharField(max_length=255, blank=True)),
                ("first_seen", models.DateTimeField(auto_now_add=True)),
                ("last_seen", models.DateTimeField(default=timezone.now, db_index=True)),
                ("device", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="topology_neighbors", to="dcim.device")),
                ("local_interface", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="topology_neighbors", to="dcim.interface")),
                ("neighbor_device", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reported_neighbors", to="dcim.device")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["device", "local_interface"], name="topology_nei_device__0f6a4f_idx"),
                    models.Index(fields=["neighbor_name"], name="topology_nei_neighbor_3b3e62_idx"),
                    models.Index(fields=["protocol"], name="topology_nei_protocol_4dd66b_idx"),
                ],
            },
        ),
    ]
