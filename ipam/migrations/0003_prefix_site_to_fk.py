import django.db.models.deletion
from django.db import migrations, models


def map_prefix_sites(apps, schema_editor):
    Prefix = apps.get_model("ipam", "Prefix")
    Site = apps.get_model("dcim", "Site")
    Organization = apps.get_model("dcim", "Organization")

    site_name_map = {}
    for site in Site.objects.all():
        site_name_map.setdefault(site.name, []).append(site)
    fallback_site = Site.objects.first()
    if not fallback_site:
        org = Organization.objects.order_by("name").first()
        if org:
            fallback_site = Site.objects.create(name="Default Site", organization=org)

    for prefix in Prefix.objects.all():
        target = None
        legacy_name = getattr(prefix, "legacy_site", None)
        if legacy_name:
            candidates = site_name_map.get(legacy_name, [])
            if len(candidates) == 1:
                target = candidates[0]
            elif candidates:
                target = candidates[0]
        if not target:
            target = fallback_site
        if target:
            prefix.site_id = target.id
            prefix.save(update_fields=["site"])


class Migration(migrations.Migration):

    dependencies = [
        ("dcim", "0004_site_hierarchy_refactor"),
        ("ipam", "0002_alter_prefix_site"),
    ]

    operations = [
        migrations.RenameField(
            model_name="prefix",
            old_name="site",
            new_name="legacy_site",
        ),
        migrations.AddField(
            model_name="prefix",
            name="site",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="prefixes",
                to="dcim.site",
            ),
        ),
        migrations.RunPython(map_prefix_sites, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="prefix",
            name="legacy_site",
        ),
        migrations.AlterField(
            model_name="prefix",
            name="site",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="prefixes",
                to="dcim.site",
            ),
        ),
    ]
