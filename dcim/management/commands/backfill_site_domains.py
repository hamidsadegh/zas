import uuid

from django.core.management.base import BaseCommand, CommandError

from dcim.models import Site, Device
from dcim.services.hostname_utils import normalize_hostname
from network.models.discovery import DiscoveryCandidate
from topology.models import TopologyNeighbor


class Command(BaseCommand):
    help = "Backfill discovery candidates and topology neighbors using site domain rules."

    def add_arguments(self, parser):
        parser.add_argument(
            "--site",
            help="Limit to a site (UUID or name).",
        )
        parser.add_argument(
            "--model",
            choices=("candidates", "neighbors", "all"),
            default="all",
            help="Which records to backfill.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show changes without writing to the database.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of rows processed per model.",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=500,
            help="Iterator chunk size.",
        )

    def handle(self, *args, **options):
        site = None
        if options.get("site"):
            site = self._resolve_site(options["site"])

        model = options["model"]
        dry_run = options["dry_run"]
        limit = options.get("limit")
        chunk_size = options["chunk_size"]

        if model in ("candidates", "all"):
            updated, scanned = self._backfill_candidates(
                site=site,
                dry_run=dry_run,
                limit=limit,
                chunk_size=chunk_size,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Discovery candidates: updated {updated} / scanned {scanned}"
                )
            )

        if model in ("neighbors", "all"):
            updated, scanned = self._backfill_neighbors(
                site=site,
                dry_run=dry_run,
                limit=limit,
                chunk_size=chunk_size,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Topology neighbors: updated {updated} / scanned {scanned}"
                )
            )

    def _resolve_site(self, value: str) -> Site:
        try:
            site_id = uuid.UUID(str(value))
        except ValueError:
            site_id = None

        if site_id:
            site = Site.objects.filter(id=site_id).first()
        else:
            site = Site.objects.filter(name__iexact=value).first()

        if not site:
            raise CommandError(f"Site not found: {value}")
        return site

    def _candidate_queryset(self, *, site: Site | None):
        qs = DiscoveryCandidate.objects.select_related("site").exclude(
            site__domain__exact=""
        )
        if site:
            qs = qs.filter(site=site)
        return qs.order_by("id")

    def _neighbor_queryset(self, *, site: Site | None):
        qs = TopologyNeighbor.objects.select_related("device", "device__site").exclude(
            device__site__domain__exact=""
        )
        if site:
            qs = qs.filter(device__site=site)
        return qs.order_by("id")

    def _backfill_candidates(self, *, site: Site | None, dry_run: bool, limit: int | None, chunk_size: int):
        qs = self._candidate_queryset(site=site)
        if limit:
            qs = qs[:limit]

        updated = 0
        scanned = 0
        for candidate in qs.iterator(chunk_size=chunk_size):
            scanned += 1
            normalized = normalize_hostname(candidate.hostname, site=candidate.site)
            if not normalized or normalized == (candidate.hostname or ""):
                continue
            updated += 1
            if not dry_run:
                candidate.hostname = normalized
                candidate.save(update_fields=["hostname"])
        return updated, scanned

    def _backfill_neighbors(self, *, site: Site | None, dry_run: bool, limit: int | None, chunk_size: int):
        qs = self._neighbor_queryset(site=site)
        if limit:
            qs = qs[:limit]

        updated = 0
        scanned = 0
        for neighbor in qs.iterator(chunk_size=chunk_size):
            scanned += 1
            normalized = normalize_hostname(
                neighbor.neighbor_name,
                site=neighbor.device.site if neighbor.device else None,
            )
            if not normalized:
                continue
            neighbor_device = Device.objects.filter(name__iexact=normalized).first()
            changed = normalized != (neighbor.neighbor_name or "")
            device_changed = (neighbor_device and neighbor.neighbor_device_id != neighbor_device.id) or (
                neighbor_device is None and neighbor.neighbor_device_id is not None
            )
            if not (changed or device_changed):
                continue
            updated += 1
            if not dry_run:
                neighbor.neighbor_name = normalized
                neighbor.neighbor_device = neighbor_device
                neighbor.save(update_fields=["neighbor_name", "neighbor_device"])
        return updated, scanned
