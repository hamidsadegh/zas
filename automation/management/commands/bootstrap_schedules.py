from django.core.management.base import BaseCommand

from automation.services.scheduler_sync import (
    sync_config_backup_schedule,
    sync_reachability_from_system_settings,
)
from accounts.services.settings_service import get_system_settings


class Command(BaseCommand):
    help = "Bootstrap and synchronize automation schedules"

    def handle(self, *args, **options):
        self.stdout.write("Bootstrapping automation schedules...")

        # --- Reachability (driven by SystemSettings) ---
        settings = get_system_settings()
        sync_reachability_from_system_settings(settings)
        self.stdout.write(
            self.style.SUCCESS("✓ Reachability schedule synchronized")
        )

        # --- Configuration backup (nightly cron) ---
        sync_config_backup_schedule()
        self.stdout.write(
            self.style.SUCCESS("✓ Configuration backup schedule synchronized")
        )

        self.stdout.write(
            self.style.SUCCESS("All automation schedules are up to date.")
        )
