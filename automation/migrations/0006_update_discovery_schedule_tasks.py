from django.db import migrations


def update_discovery_task_definitions(apps, schema_editor):
    TaskDefinition = apps.get_model("automation", "AutomationTaskDefinition")

    discovery_task = {
        "name": "Network Discovery Scan",
        "task_name": "network.tasks.run_scheduled_discovery_scan_job",
        "category": "network",
        "description": "Scheduled discovery scan using enabled discovery ranges per site.",
        "managed_by": "ui",
        "supports_schedule": True,
    }
    auto_assign_task = {
        "name": "Discovery Auto-Assign",
        "task_name": "network.tasks.run_scheduled_auto_assign_job",
        "category": "network",
        "description": "Scheduled auto-assign for unclassified discovery candidates.",
        "managed_by": "ui",
        "supports_schedule": True,
    }

    discovery_obj, _ = TaskDefinition.objects.update_or_create(
        task_name=discovery_task["task_name"],
        defaults=discovery_task,
    )
    auto_assign_obj, _ = TaskDefinition.objects.update_or_create(
        task_name=auto_assign_task["task_name"],
        defaults=auto_assign_task,
    )

    TaskDefinition.objects.filter(task_name="network.tasks.run_discovery_scan_job").exclude(
        id=discovery_obj.id
    ).delete()
    TaskDefinition.objects.filter(task_name="network.tasks.run_auto_assign_job").exclude(
        id=auto_assign_obj.id
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("automation", "0005_add_scheduled_sync_task"),
    ]

    operations = [
        migrations.RunPython(update_discovery_task_definitions, migrations.RunPython.noop),
    ]
