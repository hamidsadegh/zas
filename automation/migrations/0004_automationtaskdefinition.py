from django.db import migrations, models
import uuid


def seed_task_definitions(apps, schema_editor):
    TaskDefinition = apps.get_model("automation", "AutomationTaskDefinition")

    tasks = [
        {
            "name": "Reachability Poller",
            "task_name": "automation.tasks.run_scheduled_reachability",
            "category": "automation",
            "description": "Periodic reachability checks for tagged devices.",
            "managed_by": "system",
            "supports_schedule": True,
        },
        {
            "name": "Nightly Configuration Backup",
            "task_name": "automation.tasks.run_scheduled_config_backup",
            "category": "automation",
            "description": "Nightly configuration backups for tagged devices.",
            "managed_by": "system",
            "supports_schedule": True,
        },
        {
            "name": "Reachability History Cleanup",
            "task_name": "automation.tasks.cleanup_reachability_history",
            "category": "automation",
            "description": "Cleanup old reachability job runs.",
            "managed_by": "ui",
            "supports_schedule": True,
        },
        {
            "name": "Topology Neighbor Collection",
            "task_name": "automation.tasks.topology_collector.collect_topology_neighbors",
            "category": "automation",
            "description": "Collect CDP/LLDP neighbors from eligible devices.",
            "managed_by": "ui",
            "supports_schedule": True,
        },
        {
            "name": "Topology Neighbor Cleanup",
            "task_name": "automation.tasks.topology_collector.cleanup_topology_neighbors",
            "category": "automation",
            "description": "Cleanup stale topology neighbor records.",
            "managed_by": "ui",
            "supports_schedule": True,
        },
        {
            "name": "On-demand Reachability Job",
            "task_name": "automation.tasks.run_reachability_job",
            "category": "automation",
            "description": "Runs a reachability job for a specific run id.",
            "managed_by": "workflow",
            "supports_schedule": False,
        },
        {
            "name": "On-demand Configuration Backup",
            "task_name": "automation.tasks.run_backup_job",
            "category": "automation",
            "description": "Runs a configuration backup for a specific run id.",
            "managed_by": "workflow",
            "supports_schedule": False,
        },
        {
            "name": "Network Discovery Scan",
            "task_name": "network.tasks.run_discovery_scan_job",
            "category": "network",
            "description": "Discovery scan job triggered from the discovery workflow.",
            "managed_by": "workflow",
            "supports_schedule": False,
        },
        {
            "name": "Discovery Auto-Assign",
            "task_name": "network.tasks.run_auto_assign_job",
            "category": "network",
            "description": "Auto-assign candidates triggered from the discovery workflow.",
            "managed_by": "workflow",
            "supports_schedule": False,
        },
        {
            "name": "Celery Debug Task",
            "task_name": "zas.celery.debug_task",
            "category": "system",
            "description": "Celery debug task used for diagnostics.",
            "managed_by": "system",
            "supports_schedule": False,
        },
    ]

    for task in tasks:
        TaskDefinition.objects.update_or_create(
            task_name=task["task_name"],
            defaults=task,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("automation", "0003_alter_automationjob_created_at_alter_jobrun_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="AutomationTaskDefinition",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=120)),
                ("task_name", models.CharField(max_length=200, unique=True)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("automation", "Automation"),
                            ("network", "Network"),
                            ("system", "System"),
                        ],
                        default="automation",
                        max_length=20,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                (
                    "managed_by",
                    models.CharField(
                        choices=[
                            ("ui", "Automation UI"),
                            ("system", "System Settings"),
                            ("workflow", "Workflow / UI"),
                        ],
                        default="ui",
                        max_length=20,
                    ),
                ),
                ("supports_schedule", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["category", "name"],
            },
        ),
        migrations.RunPython(seed_task_definitions, migrations.RunPython.noop),
    ]
