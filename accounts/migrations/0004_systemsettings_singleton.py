from django.db import migrations


def ensure_singleton(apps, schema_editor):
    SystemSettings = apps.get_model("accounts", "SystemSettings")
    records = list(
        SystemSettings.objects.order_by("-updated_at", "pk").values()
    )

    if not records:
        SystemSettings.objects.create(pk=1)
        return

    latest = records[0]
    defaults = {key: value for key, value in latest.items() if key != "id"}

    SystemSettings.objects.update_or_create(pk=1, defaults=defaults)
    SystemSettings.objects.exclude(pk=1).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_systemsettings_reachability"),
    ]

    operations = [
        migrations.RunPython(ensure_singleton, migrations.RunPython.noop),
    ]
