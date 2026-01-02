from django.core.management.base import BaseCommand, CommandError

from network.services.discover_network import NetworkDiscoveryService
from dcim.models.site import Organization, Site


class Command(BaseCommand):
    help = "Run network discovery for a site"

    def add_arguments(self, parser):
        parser.add_argument(
            "--site",
            help="Site name (may require --org if not unique)",
        )
        parser.add_argument(
            "--org",
            help="Organization name (recommended if site names are reused)",
        )
        parser.add_argument(
            "--site-id",
            help="Site UUID (automation / unambiguous)",
        )

    def handle(self, *args, **options):
        site_id = options.get("site_id")
        site_name = options.get("site")
        org_name = options.get("org")

        if site_id:
            site = self._get_site_by_id(site_id)
        elif site_name:
            site = self._get_site_by_name(site_name, org_name)
        else:
            raise CommandError(
                "You must provide either --site-id or --site (optionally with --org)"
            )

        self.stdout.write(
            self.style.NOTICE(f"Starting discovery for site: {site}")
        )

        if site_id:
            service = NetworkDiscoveryService(site_id=site.id)
        elif site_name:
            service = NetworkDiscoveryService(site=site)
        else:
            raise CommandError("Invalid site specification")
        
        stats = service.run()

        self.stdout.write(
            self.style.SUCCESS(
                "Discovery finished:\n"
                f"  Ranges scanned : {stats['ranges']}\n"
                f"  Alive found    : {stats['alive']}\n"
                f"  Exact matches  : {stats.get('exact', 0)}\n"
                f"  Mismatches     : {stats.get('mismatch', 0)}\n"
                f"  New devices  : {stats.get('new', 0)}"
            )
        )

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    def _get_site_by_id(self, site_id):
        try:
            return Site.objects.get(id=site_id)
        except Site.DoesNotExist:
            raise CommandError(f"Site with id {site_id} does not exist")

    def _get_site_by_name(self, site_name, org_name):
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
                f"Multiple sites named '{site_name}'. "
                "Please specify --org or use --site-id."
            )

        return qs.first()
