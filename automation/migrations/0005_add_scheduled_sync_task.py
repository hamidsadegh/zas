from django.db import migrations


def seed_scheduled_sync_task(apps, schema_editor):
    TaskDefinition = apps.get_model("automation", "AutomationTaskDefinition")

    TaskDefinition.objects.update_or_create(
        task_name="network.tasks.run_scheduled_sync_job",
        defaults={
            "name": "Scheduled Device Sync",
            "category": "network",
            "description": "Automated device sync for active devices excluding tag 'no_sync'.",
            "managed_by": "ui",
            "supports_schedule": True,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("automation", "0004_automationtaskdefinition"),
    ]

    operations = [
        migrations.RunPython(seed_scheduled_sync_task, migrations.RunPython.noop),
    ]
