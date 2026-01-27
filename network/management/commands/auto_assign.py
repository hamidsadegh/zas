from django.core.management.base import BaseCommand, CommandError

from network.models.discovery import DiscoveryCandidate
from network.services.auto_assignment_service import AutoAssignmentService


class Command(BaseCommand):
    help = "Auto-assign discovered candidates into DCIM"

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

    def handle(self, *args, **options):
        candidate_id = options.get("candidate_id")
        candidate_hostname = options.get("candidate_hostname")
        site_id = options.get("site_id")
        limit = options.get("limit")
        include_config = not options.get("no_config", False)

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

        if not qs.exists():
            self.stdout.write(self.style.NOTICE("No pending candidates to assign."))
            return

        success = 0
        failed = 0
        failures = []
        for candidate in qs:
            self.stdout.write(self.style.NOTICE(f"Assigning candidate {candidate.hostname or candidate.ip_address}"))
            try:
                result = AutoAssignmentService(candidate, include_config=include_config).assign()
            except Exception as exc:
                result = {"success": False, "error": str(exc), "device": None}
            if result.get("success"):
                success += 1
                device = result.get("device")
                self.stdout.write(self.style.SUCCESS(f"[OK] {device}"))
            else:
                failed += 1
                error_msg = result.get("error") or "Unknown error"
                failures.append((candidate, error_msg))
                self.stdout.write(self.style.ERROR(f"[FAIL] {error_msg}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Auto-assignment finished. Success: {success}, Failed: {failed}"
            )
        )
        if failures:
            self.stdout.write(self.style.ERROR("Failed candidates:"))
            for candidate, error_msg in failures:
                label = candidate.hostname or str(candidate.ip_address)
                self.stdout.write(self.style.ERROR(f"  - {label}: {error_msg}"))
