import os

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from dcim.models import Site, VLAN


class Command(BaseCommand):
    help = "Import VLANs from Berlin and Bonn Excel workbooks."

    def add_arguments(self, parser):
        parser.add_argument(
            "--berlin",
            default=os.path.join(settings.BASE_DIR, "data/imports/vlans/", "berlin.xlsx"),
            help="Path to Berlin Excel file",
        )
        parser.add_argument(
            "--bonn",
            default=os.path.join(settings.BASE_DIR, "data/imports/vlans/", "bonn.xls"),
            help="Path to Bonn Excel file",
        )

    def handle(self, *args, **options):
        paths = {
            "Berlin": options["berlin"],
            "Bonn": options["bonn"],
        }
        created = 0
        updated = 0

        for site_name, path in paths.items():
            if not os.path.exists(path):
                raise CommandError(f"File not found: {path}")
            self.stdout.write(f"Processing {site_name} file: {path}")

            site_obj = Site.objects.filter(name=site_name).order_by("organization__name").first()
            if not site_obj:
                raise CommandError(f"Unable to locate site '{site_name}' to attach VLANs.")

            df = pd.read_excel(path)
            df.columns = [col.strip().lower() for col in df.columns]

            for _, row in df.iterrows():
                vlan_id = row.get("vlan id")
                name = row.get("name")
                subnet = row.get("subnet")
                gateway = row.get("gateway")
                usage_area = row.get("usage area")
                description = row.get("description")    

                if pd.isna(vlan_id):
                    continue

                obj, created_flag = VLAN.objects.update_or_create(
                    site=site_obj,
                    vlan_id=int(vlan_id),
                    defaults={
                        "name": None if pd.isna(name) else str(name).strip(),
                        "subnet": str(subnet).strip(),
                        "gateway": None if pd.isna(gateway) else str(gateway).strip(),
                        "usage_area": usage_area if usage_area in dict(VLAN.USAGE_CHOICES) else "Sonstiges",
                        "description": None if pd.isna(description) else str(description).strip(),
                    },
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(f"Import completed. Created: {created}, Updated: {updated}"))
