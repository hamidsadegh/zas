from concurrent.futures import ThreadPoolExecutor, as_completed

from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.utils import timezone

from automation.tasks.topology_collector import (
    collect_neighbors_for_device,
    collect_topology_neighbors,
    get_eligible_devices,
)


class Command(BaseCommand):
    help = "Collect CDP/LLDP neighbors for eligible devices."

    def add_arguments(self, parser):
        parser.add_argument(
            "--device-id",
            dest="device_id",
            default=None,
            help="Collect neighbors for a single device UUID.",
        )
        parser.add_argument(
            "--device-name",
            dest="device_name",
            default=None,
            help="Collect neighbors for a single device name.",
        )
        parser.add_argument(
            "--site",
            dest="site_name",
            default=None,
            help="Collect neighbors for devices in a specific site name.",
        )
        parser.add_argument(
            "--tag",
            dest="tag_name",
            default=None,
            help="Collect neighbors for devices with a specific tag name.",
        )
        parser.add_argument(
            "--async",
            dest="run_async",
            action="store_true",
            help="Queue collection via Celery instead of running inline.",
        )
        parser.add_argument(
            "--threads",
            type=int,
            default=10,
            help="Number of parallel threads for inline run (default: 10).",
        )

    def handle(self, *args, **options):
        device_id = options["device_id"]
        device_name = options["device_name"]
        run_async = options["run_async"]
        threads = options.get("threads") or 1
        if threads < 1:
            threads = 1
        site_name = options.get("site_name")
        tag_name = options.get("tag_name")

        if device_id and device_name:
            self.stderr.write(self.style.ERROR("Use only one of --device-id or --device-name."))
            return

        if device_name and not device_id:
            from dcim.models import Device
            device = Device.objects.filter(name__iexact=device_name).first()
            if not device:
                self.stderr.write(self.style.ERROR(f"No device found with name '{device_name}'."))
                return
            device_id = str(device.id)

        if run_async:
            if site_name or tag_name:
                self.stderr.write(
                    self.style.ERROR("--site and --tag are only supported for inline runs.")
                )
                return
            task = collect_topology_neighbors.delay(device_id=device_id)
            self.stdout.write(self.style.SUCCESS(f"Queued topology collection task: {task.id}"))
            return

        devices = list(get_eligible_devices())
        if site_name:
            devices = [device for device in devices if device.site.name.lower() == site_name.lower()]
        if tag_name:
            devices = [device for device in devices if device.tags.filter(name__iexact=tag_name).exists()]
        if device_id:
            devices = [device for device in devices if str(device.id) == str(device_id)]

        success = 0
        failed = 0

        if threads == 1 or len(devices) <= 1:
            for device in devices:
                if collect_neighbors_for_device(device):
                    success += 1
                    self.stdout.write(self.style.SUCCESS(f"[OK] {device.name}"))
                else:
                    failed += 1
                    self.stdout.write(self.style.ERROR(f"[FAIL] {device.name}"))
        else:
            max_workers = min(threads, len(devices))
            self.stdout.write(self.style.NOTICE(f"Using {max_workers} threads"))

            def _worker(target_device):
                close_old_connections()
                try:
                    return collect_neighbors_for_device(target_device)
                finally:
                    close_old_connections()

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(_worker, device): device for device in devices}
                for future in as_completed(futures):
                    device = futures[future]
                    try:
                        ok = future.result()
                    except Exception:
                        ok = False
                    if ok:
                        success += 1
                        self.stdout.write(self.style.SUCCESS(f"[OK] {device.name}"))
                    else:
                        failed += 1
                        self.stdout.write(self.style.ERROR(f"[FAIL] {device.name}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Topology collection finished at {timezone.now():%Y-%m-%d %H:%M}. "
                f"Success: {success}, Failed: {failed}"
            )
        )
