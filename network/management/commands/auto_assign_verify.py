from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from dcim.models import DeviceModule, DeviceStackMember
from network.models.discovery import DiscoveryCandidate
from network.services.auto_assignment_service import AutoAssignmentService


class Command(BaseCommand):
    help = "Auto-assign candidates and print detailed verification output"

    def add_arguments(self, parser):
        parser.add_argument(
            "--site-id",
            help="Limit to candidates for a specific Site UUID",
        )
        parser.add_argument(
            "--candidate-id",
            help="Assign a single candidate UUID",
        )
        parser.add_argument(
            "--candidate-hostname",
            help="Assign candidates matching hostname (case-insensitive substring)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of candidates to process",
        )
        parser.add_argument(
            "--no-config",
            action="store_true",
            help="Skip running-config collection after assignment",
        )
        parser.add_argument(
            "--show-raw",
            action="store_true",
            help="Print raw command output gathered during assignment",
        )
        parser.add_argument(
            "--show-parsed",
            action="store_true",
            help="Print parsed command output gathered during assignment",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Print full candidate/device snapshot",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Collect details without writing to the database",
        )

    def handle(self, *args, **options):
        qs = self._resolve_candidates(options)
        if not qs.exists():
            self.stdout.write(self.style.NOTICE("No pending candidates to assign."))
            return

        include_config = not options.get("no_config", False)
        show_raw = options.get("show_raw")
        show_parsed = options.get("show_parsed")
        verbose = options.get("verbose")
        dry_run = options.get("dry_run")

        success = 0
        failed = 0
        failures = []

        self.stdout.write(
            self.style.NOTICE(
                f"Starting auto-assign verify at {timezone.now():%Y-%m-%d %H:%M} ({qs.count()} candidates)"
            )
        )

        for candidate in qs:
            label = candidate.hostname or str(candidate.ip_address)
            self.stdout.write(self.style.NOTICE(f"Assigning candidate {label}"))
            if dry_run:
                try:
                    result = AutoAssignmentService(
                        candidate,
                        include_config=include_config,
                    ).collect_details()
                except Exception as exc:
                    result = {"success": False, "error": str(exc), "device": None}
            else:
                try:
                    result = AutoAssignmentService(
                        candidate,
                        include_config=include_config,
                    ).assign(return_details=bool(show_raw or show_parsed or verbose))
                except Exception as exc:
                    result = {"success": False, "error": str(exc), "device": None}

            if result.get("success"):
                success += 1
                device = result.get("device")
                label = device if device else (candidate.hostname or candidate.ip_address)
                status = "[DRY-RUN OK]" if dry_run else "[OK]"
                self.stdout.write(self.style.SUCCESS(f"{status} {label}"))
                if show_raw or show_parsed or verbose:
                    self._print_details(
                        candidate=candidate,
                        device=device,
                        details=result.get("details") or {},
                        show_raw=show_raw,
                        show_parsed=show_parsed,
                        verbose=verbose,
                    )
            else:
                failed += 1
                error_msg = result.get("error") or "Unknown error"
                failures.append((candidate, error_msg))
                self.stdout.write(self.style.ERROR(f"[FAIL] {error_msg}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Auto-assign verify finished at {timezone.now():%Y-%m-%d %H:%M}. "
                f"Success: {success}, Failed: {failed}"
            )
        )
        if failures:
            self.stdout.write(self.style.ERROR("Failed candidates:"))
            for candidate, error_msg in failures:
                label = candidate.hostname or str(candidate.ip_address)
                self.stdout.write(self.style.ERROR(f"  - {label}: {error_msg}"))

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------
    def _resolve_candidates(self, options):
        candidate_id = options.get("candidate_id")
        candidate_hostname = options.get("candidate_hostname")
        site_id = options.get("site_id")
        limit = options.get("limit")

        qs = DiscoveryCandidate.objects.filter(accepted__isnull=True, classified=False)
        if site_id:
            qs = qs.filter(site_id=site_id)

        if candidate_id:
            qs = qs.filter(id=candidate_id)
            if not qs.exists():
                raise CommandError(f"No candidate found with id '{candidate_id}'")

        if candidate_hostname:
            qs = qs.filter(hostname__icontains=candidate_hostname)
            if not qs.exists():
                raise CommandError(
                    f"No candidate found with hostname containing '{candidate_hostname}'"
                )

        if limit and limit > 0:
            qs = qs[:limit]

        return qs

    def _print_details(
        self,
        *,
        candidate: DiscoveryCandidate,
        device,
        details: dict,
        show_raw: bool,
        show_parsed: bool,
        verbose: bool,
    ) -> None:
        if verbose:
            self.stdout.write("  Candidate snapshot:")
            self.stdout.write(
                f"    hostname={candidate.hostname} ip={candidate.ip_address} "
                f"site={candidate.site} classified={candidate.classified} accepted={candidate.accepted}"
            )
            if device:
                self.stdout.write("  Device snapshot:")
                self.stdout.write(
                    f"    name={device.name} ip={device.management_ip} "
                    f"site={device.site} area={device.area} rack={device.rack} position={device.position}"
                )
                self.stdout.write(
                    f"    type={device.device_type} role={device.role} status={device.status} "
                    f"is_stacked={device.is_stacked}"
                )
                self.stdout.write(f"    tags={sorted(device.tags.values_list('name', flat=True))}")
                self.stdout.write(
                    f"    modules={DeviceModule.objects.filter(device=device).count()} "
                    f"stack_members={DeviceStackMember.objects.filter(device=device).count()}"
                )

        if show_raw or show_parsed:
            self.stdout.write("  Assignment details:")
            if show_raw:
                for key in ("version_raw", "location_raw", "stack_raw"):
                    raw = details.get(key) or ""
                    if not raw:
                        continue
                    label = key.replace("_", " ")
                    self.stdout.write(self.style.WARNING(f"    {label}:"))
                    for line in raw.splitlines():
                        self.stdout.write(f"      {line}")
            if show_parsed:
                self.stdout.write(f"    parsed_version: {details.get('parsed_version')}")
                self.stdout.write(f"    stack_members: {details.get('stack_members')}")
                self.stdout.write(
                    f\"    area={details.get('area_name')} rack={details.get('rack_name')} unit={details.get('requested_unit')}\"
                )
                self.stdout.write(f"    model_name: {details.get('model_name')}")
                self.stdout.write(f"    device_type: {details.get('device_type')}")
                if details.get("tags"):
                    self.stdout.write(f\"    tags: {details.get('tags')}\")
