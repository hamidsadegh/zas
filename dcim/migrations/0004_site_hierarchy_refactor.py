import uuid

import django.db.models.deletion
from django.db import migrations, models


def assign_sites(apps, schema_editor):
    Organization = apps.get_model("dcim", "Organization")
    Site = apps.get_model("dcim", "Site")
    Area = apps.get_model("dcim", "Area")
    Device = apps.get_model("dcim", "Device")
    VLAN = apps.get_model("dcim", "VLAN")
    SiteCredential = apps.get_model("accounts", "SiteCredential")
    Prefix = apps.get_model("ipam", "Prefix")

    default_org = Organization.objects.order_by("name").first()

    def ensure_site(org, name):
        org = org or default_org
        if not org:
            return None
        label = (name or "").strip() or f"{org.name} Site"
        site, _ = Site.objects.get_or_create(
            organization=org,
            name=label,
            defaults={"description": "Migrated from legacy hierarchy"},
        )
        return site

    # Pre-create site objects for known organization/site name pairs
    legacy_pairs = set()
    for device in Device.objects.exclude(legacy_site__isnull=True).exclude(legacy_site="").select_related("organization"):
        legacy_pairs.add((device.organization_id, device.legacy_site))
    for org_id, site_name in legacy_pairs:
        org = Organization.objects.filter(id=org_id).first()
        ensure_site(org, site_name)

    # Ensure sites exist for site-only models so assignments succeed later
    for credential in SiteCredential.objects.exclude(site="").all():
        ensure_site(default_org, credential.site)
    for prefix in Prefix.objects.exclude(site="").all():
        ensure_site(default_org, prefix.site)
    for vlan in VLAN.objects.exclude(legacy_site__isnull=True).exclude(legacy_site="").all():
        ensure_site(default_org, vlan.legacy_site)

    # Map areas to sites based on their top-most ancestor
    area_site_map = {}
    site_cache = {}
    for area in Area.objects.select_related("organization", "parent").all():
        root = area
        visited = set()
        while root.parent_id:
            if root.id in visited:
                break
            visited.add(root.id)
            root = root.parent
        site = ensure_site(getattr(area, "organization", None), getattr(root, "name", None))
        if site:
            area.site_id = site.id
            area.save(update_fields=["site"])
            area_site_map[area.id] = site.id
            site_cache[site.id] = site

    # Assign devices to the derived sites
    for device in Device.objects.select_related("organization", "area").all():
        site = None
        if device.area_id and device.area_id in area_site_map:
            site_id = area_site_map[device.area_id]
            site = site_cache.get(site_id) or Site.objects.filter(id=site_id).first()
            site_cache[site_id] = site
        legacy_name = getattr(device, "legacy_site", None)
        if not site and legacy_name:
            site = ensure_site(getattr(device, "organization", None), legacy_name)
        if not site:
            site = ensure_site(getattr(device, "organization", None), None)
        if site:
            device.site_id = site.id
            device.save(update_fields=["site"])

    # Assign VLANs by matching on site name, falling back to the first site
    by_name = {}
    for site in Site.objects.all():
        by_name.setdefault(site.name, []).append(site)
    fallback_site = Site.objects.first()
    for vlan in VLAN.objects.all():
        assigned = None
        legacy_name = getattr(vlan, "legacy_site", None)
        if legacy_name:
            candidates = by_name.get(legacy_name, [])
            if len(candidates) == 1:
                assigned = candidates[0]
            elif candidates:
                assigned = candidates[0]
        if not assigned:
            assigned = fallback_site
        if assigned:
            vlan.site_id = assigned.id
            vlan.save(update_fields=["site"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_rename_reachability_telemetry_enabled_systemsettings_reachability_netconf_enabled"),
        ("ipam", "0002_alter_prefix_site"),
        ("dcim", "0003_device_last_reboot_device_uptime"),
    ]

    operations = [
        migrations.CreateModel(
            name="Site",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sites",
                        to="dcim.organization",
                    ),
                ),
            ],
            options={
                "verbose_name": "Site",
                "verbose_name_plural": "Sites",
                "ordering": ("organization__name", "name"),
                "unique_together": {("organization", "name")},
            },
        ),
        migrations.AddField(
            model_name="area",
            name="site",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="areas",
                help_text="Site that contains this area.",
                to="dcim.site",
            ),
        ),
        migrations.RenameField(
            model_name="device",
            old_name="site",
            new_name="legacy_site",
        ),
        migrations.AddField(
            model_name="device",
            name="site",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="devices",
                to="dcim.site",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="vlan",
            unique_together=set(),
        ),
        migrations.RenameField(
            model_name="vlan",
            old_name="site",
            new_name="legacy_site",
        ),
        migrations.AddField(
            model_name="vlan",
            name="site",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="vlans",
                to="dcim.site",
            ),
        ),
        migrations.RunPython(assign_sites, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="area",
            name="organization",
        ),
        migrations.RemoveField(
            model_name="device",
            name="organization",
        ),
        migrations.RemoveField(
            model_name="device",
            name="legacy_site",
        ),
        migrations.RemoveField(
            model_name="vlan",
            name="legacy_site",
        ),
        migrations.AlterField(
            model_name="area",
            name="site",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="areas",
                help_text="Site that contains this area.",
                to="dcim.site",
            ),
        ),
        migrations.AlterField(
            model_name="device",
            name="site",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="devices",
                to="dcim.site",
            ),
        ),
        migrations.AlterField(
            model_name="vlan",
            name="site",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="vlans",
                to="dcim.site",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="vlan",
            unique_together={("site", "vlan_id")},
        ),
        migrations.AlterUniqueTogether(
            name="area",
            unique_together={("site", "name", "parent")},
        ),
    ]
