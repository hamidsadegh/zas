from django.core.management.base import BaseCommand
from automation.services.scheduler_sync import (
    sync_config_backup_schedule,
)

class Command(BaseCommand):
    help = "Bootstrap automation schedules"

    def handle(self, *args, **options):
        sync_config_backup_schedule()
        self.stdout.write(self.style.SUCCESS("Configuration backup schedule ensured"))
