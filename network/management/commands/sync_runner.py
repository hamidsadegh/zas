from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from dcim.models import Device
from dcim.models.site import Organization, Site
from network.services.sync_service import SyncService


class Command(BaseCommand):
    help = "Run SSH sync for all devices in a site or a single device"

    def add_arguments(self, parser):
        parser.add_argument("--site", help="Site name (may require --org if not unique)")
        parser.add_argument("--org", help="Organization name (recommended if site names are reused)")
        parser.add_argument("--site-id", help="Site UUID (automation / unambiguous)")
        parser.add_argument("--limit", type=int, help="Limit number of devices to sync")
        parser.add_argument("--device", help="Limit sync to a specific device name")
        parser.add_argument(
            "--no-config",
            action="store_true",
            help="Skip running-config collection",
        )

    def handle(self, *args, **options):
        device_name = options.get("device")

        if device_name:
            devices = list(Device.objects.filter(name__iexact=device_name))
            if not devices:
                raise CommandError(f"No device found with name '{device_name}'.")
            if len(devices) > 1:
                raise CommandError(f"Multiple devices named '{device_name}'. Please narrow the query.")
            device = devices[0]
            service = SyncService(site=device.site)
            self.stdout.write(self.style.NOTICE(f"Starting sync for device: {device.name} ({device.site})"))
            result = service.sync_device(device, include_config=not options.get("no_config", False))
            if result.get("success"):
                self.stdout.write(self.style.SUCCESS(f"[OK] {device.name}"))
            else:
                self.stdout.write(self.style.ERROR(f"[FAIL] {device.name}: {result.get('error')}"))
            return

        site = self._resolve_site(options)
        qs = Device.objects.filter(site=site).order_by("name")
        limit = options.get("limit")
        if limit and limit > 0:
            qs = qs[:limit]

        self.stdout.write(self.style.NOTICE(f"Starting sync for site: {site} ({qs.count()} devices)"))

        service = SyncService(site=site)
        success = 0
        failed = 0
        for device in qs:
            result = service.sync_device(device, include_config=not options.get("no_config", False))
            if result.get("success"):
                success += 1
                self.stdout.write(self.style.SUCCESS(f"[OK] {device.name}"))
            else:
                failed += 1
                self.stdout.write(self.style.ERROR(f"[FAIL] {device.name}: {result.get('error')}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Sync finished at {timezone.now():%Y-%m-%d %H:%M}. Success: {success}, Failed: {failed}"
            )
        )

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------
    def _resolve_site(self, options):
        site_id = options.get("site_id")
        site_name = options.get("site")
        org_name = options.get("org")

        if site_id:
            try:
                return Site.objects.get(id=site_id)
            except Site.DoesNotExist:
                raise CommandError(f"Site with id {site_id} does not exist")

        if site_name:
            qs = Site.objects.filter(name__iexact=site_name)
            if org_name:
                try:
                    org = Organization.objects.get(name__iexact=org_name)
                except Organization.DoesNotExist:
                    raise CommandError(f"Organization '{org_name}' does not exist")
                qs = qs.filter(organization=org)

            count = qs.count()
            if count == 0:
                raise CommandError(f"No site found with name '{site_name}'")
            if count > 1:
                raise CommandError(
                    f"Multiple sites named '{site_name}'. Please specify --org or use --site-id."
                )
            return qs.first()

        raise CommandError("You must provide either --device <name> or --site <name> (optionally with --org)")
