import django.db.models.deletion
from django.db import migrations, models


def map_site_credentials(apps, schema_editor):
    SiteCredential = apps.get_model("accounts", "SiteCredential")
    Site = apps.get_model("dcim", "Site")
    Organization = apps.get_model("dcim", "Organization")

    name_map = {}
    for site in Site.objects.all():
        name_map.setdefault(site.name, []).append(site)
    fallback_site = Site.objects.first()
    if not fallback_site:
        org = Organization.objects.order_by("name").first()
        if org:
            fallback_site = Site.objects.create(name="Default Site", organization=org)

    for credential in SiteCredential.objects.all():
        target = None
        legacy_name = getattr(credential, "legacy_site", None)
        if legacy_name:
            candidates = name_map.get(legacy_name, [])
            if len(candidates) == 1:
                target = candidates[0]
            elif candidates:
                target = candidates[0]
        if not target:
            target = fallback_site
        if target:
            credential.site_id = target.id
            credential.save(update_fields=["site"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_rename_reachability_telemetry_enabled_systemsettings_reachability_netconf_enabled"),
        ("dcim", "0004_site_hierarchy_refactor"),
    ]

    operations = [
        migrations.RenameField(
            model_name="sitecredential",
            old_name="site",
            new_name="legacy_site",
        ),
        migrations.AddField(
            model_name="sitecredential",
            name="site",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="credentials",
                to="dcim.site",
            ),
        ),
        migrations.RunPython(map_site_credentials, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="sitecredential",
            name="legacy_site",
        ),
        migrations.AlterField(
            model_name="sitecredential",
            name="site",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="credentials",
                to="dcim.site",
            ),
        ),
    ]
