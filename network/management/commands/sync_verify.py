from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from dcim.models import Device, DeviceModule, DeviceStackMember, Interface
from dcim.models.site import Organization, Site
from network.services.sync_service import SyncService


@dataclass(frozen=True)
class InterfaceSnapshot:
    status: str
    speed: int | None
    speed_mode: str | None
    duplex: str | None
    ip_address: str | None
    vlan_raw: str | None
    description: str | None
    is_trunk: bool
    access_vlan: int | None
    native_vlan: int | None
    lag: str | None


class Command(BaseCommand):
    help = "Run sync against a small staging set and report diffs"

    def add_arguments(self, parser):
        parser.add_argument("--site", help="Site name (may require --org if not unique)")
        parser.add_argument("--org", help="Organization name (recommended if site names are reused)")
        parser.add_argument("--site-id", help="Site UUID (automation / unambiguous)")
        parser.add_argument("--device", action="append", help="Device name (can be used multiple times)")
        parser.add_argument("--limit", type=int, help="Limit number of devices to sync")
        parser.add_argument(
            "--with-config",
            action="store_true",
            help="Collect running-config during sync",
        )
        parser.add_argument(
            "--show-raw",
            action="store_true",
            help="Print raw command output from the device",
        )
        parser.add_argument(
            "--show-parsed",
            action="store_true",
            help="Print parsed command output from TextFSM",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Print full before/after snapshots",
        )

    def handle(self, *args, **options):
        devices = self._resolve_devices(options)
        if not devices:
            raise CommandError("No devices matched the selection.")

        include_config = options.get("with_config", False)
        success = 0
        failed = 0

        self.stdout.write(
            self.style.NOTICE(
                f"Starting sync verify at {timezone.now():%Y-%m-%d %H:%M} ({len(devices)} devices)"
            )
        )

        for device in devices:
            before = self._capture_state(device)
            service = SyncService(site=device.site)
            show_raw = options.get("show_raw")
            show_parsed = options.get("show_parsed")
            result = service.sync_device(
                device,
                include_config=include_config,
                return_results=bool(show_raw or show_parsed),
            )
            if not result.get("success"):
                failed += 1
                self.stdout.write(self.style.ERROR(f"[FAIL] {device.name}: {result.get('error')}"))
                continue

            after = self._capture_state(device)
            diff = self._diff_states(before, after)
            success += 1
            self._print_diff(device.name, diff)
            if show_raw or show_parsed:
                self._print_results(
                    device.name,
                    result.get("results") or {},
                    show_raw=show_raw,
                    show_parsed=show_parsed,
                )
            if options.get("verbose"):
                self._print_snapshot(device.name, "before", before)
                self._print_snapshot(device.name, "after", after)

        self.stdout.write(
            self.style.SUCCESS(
                f"Sync verify finished at {timezone.now():%Y-%m-%d %H:%M}. Success: {success}, Failed: {failed}"
            )
        )

    # -------------------------------------------------
    # Snapshot + diff helpers
    # -------------------------------------------------
    def _capture_state(self, device: Device) -> dict:
        device.refresh_from_db()
        return {
            "device_fields": {
                "serial_number": device.serial_number or "",
                "image_version": device.image_version or "",
                "uptime_seconds": int(device.uptime.total_seconds()) if device.uptime else None,
                "last_reboot": device.last_reboot.isoformat() if device.last_reboot else "",
                "is_stacked": device.is_stacked,
            },
            "interfaces": self._interface_snapshot(device),
            "modules": self._module_snapshot(device),
            "stack_members": self._stack_snapshot(device),
        }

    @staticmethod
    def _interface_snapshot(device: Device) -> dict[str, InterfaceSnapshot]:
        items = Interface.objects.filter(device=device).select_related("lag")
        snapshot = {}
        for iface in items:
            snapshot[iface.name] = InterfaceSnapshot(
                status=iface.status or "",
                speed=iface.speed,
                speed_mode=iface.speed_mode,
                duplex=iface.duplex,
                ip_address=str(iface.ip_address) if iface.ip_address else None,
                vlan_raw=iface.vlan_raw or None,
                description=iface.description or None,
                is_trunk=bool(iface.is_trunk),
                access_vlan=iface.access_vlan.vlan_id if iface.access_vlan else None,
                native_vlan=iface.native_vlan.vlan_id if iface.native_vlan else None,
                lag=iface.lag.name if iface.lag else None,
            )
        return snapshot

    @staticmethod
    def _module_snapshot(device: Device) -> set[tuple[str, str]]:
        return set(
            DeviceModule.objects.filter(device=device)
            .values_list("name", "serial_number")
        )

    @staticmethod
    def _stack_snapshot(device: Device) -> set[int]:
        return set(
            DeviceStackMember.objects.filter(device=device)
            .values_list("switch_number", flat=True)
        )

    def _diff_states(self, before: dict, after: dict) -> dict:
        return {
            "device_fields": self._diff_dict(before["device_fields"], after["device_fields"]),
            "interfaces": self._diff_maps(before["interfaces"], after["interfaces"]),
            "modules": self._diff_sets(before["modules"], after["modules"]),
            "stack_members": self._diff_sets(before["stack_members"], after["stack_members"]),
        }

    @staticmethod
    def _diff_dict(before: dict, after: dict) -> dict:
        changed = {}
        for key in before.keys() | after.keys():
            if before.get(key) != after.get(key):
                changed[key] = (before.get(key), after.get(key))
        return changed

    @staticmethod
    def _diff_sets(before: set, after: set) -> dict:
        return {
            "added": sorted(after - before),
            "removed": sorted(before - after),
        }

    @staticmethod
    def _diff_maps(before: dict, after: dict) -> dict:
        before_keys = set(before)
        after_keys = set(after)
        added = sorted(after_keys - before_keys)
        removed = sorted(before_keys - after_keys)
        changed = {}
        for key in sorted(before_keys & after_keys):
            if before[key] != after[key]:
                changed[key] = (before[key], after[key])
        return {
            "added": added,
            "removed": removed,
            "changed": changed,
        }

    def _print_diff(self, device_name: str, diff: dict) -> None:
        self.stdout.write(self.style.SUCCESS(f"[OK] {device_name}"))

        device_changes = diff["device_fields"]
        if device_changes:
            self.stdout.write("  Device fields:")
            for key, (before, after) in device_changes.items():
                self.stdout.write(f"    - {key}: {before} -> {after}")

        iface_diff = diff["interfaces"]
        if iface_diff["added"] or iface_diff["removed"] or iface_diff["changed"]:
            self.stdout.write("  Interfaces:")
            if iface_diff["added"]:
                self.stdout.write(f"    + {', '.join(iface_diff['added'])}")
            if iface_diff["removed"]:
                self.stdout.write(f"    - {', '.join(iface_diff['removed'])}")
            if iface_diff["changed"]:
                for name, (before, after) in iface_diff["changed"].items():
                    self.stdout.write(f"    * {name}: {before} -> {after}")

        module_diff = diff["modules"]
        if module_diff["added"] or module_diff["removed"]:
            self.stdout.write("  Modules:")
            if module_diff["added"]:
                self.stdout.write(f"    + {module_diff['added']}")
            if module_diff["removed"]:
                self.stdout.write(f"    - {module_diff['removed']}")

        stack_diff = diff["stack_members"]
        if stack_diff["added"] or stack_diff["removed"]:
            self.stdout.write("  Stack members:")
            if stack_diff["added"]:
                self.stdout.write(f"    + {stack_diff['added']}")
            if stack_diff["removed"]:
                self.stdout.write(f"    - {stack_diff['removed']}")

    def _print_snapshot(self, device_name: str, label: str, snapshot: dict) -> None:
        self.stdout.write(f"  Snapshot ({label}): {device_name}")
        self.stdout.write(f"    device_fields: {snapshot['device_fields']}")
        self.stdout.write(f"    interfaces: {snapshot['interfaces']}")
        self.stdout.write(f"    modules: {sorted(snapshot['modules'])}")
        self.stdout.write(f"    stack_members: {sorted(snapshot['stack_members'])}")

    def _print_results(self, device_name: str, results: dict, *, show_raw: bool, show_parsed: bool) -> None:
        if not results:
            return
        self.stdout.write(f"  Device output ({device_name}):")
        for command, payload in results.items():
            if not isinstance(payload, dict):
                continue
            self.stdout.write(self.style.WARNING(f"    {command}:"))
            if show_raw:
                raw = payload.get("raw") or ""
                self.stdout.write("      raw:")
                for line in raw.splitlines():
                    self.stdout.write(f"        {line}")
            if show_parsed:
                parsed = payload.get("parsed")
                self.stdout.write(f"      parsed: {parsed}")

    # -------------------------------------------------
    # Selection helpers
    # -------------------------------------------------
    def _resolve_devices(self, options) -> list[Device]:
        device_names = options.get("device") or []
        if device_names:
            devices = list(Device.objects.filter(name__in=device_names))
            return self._apply_limit(devices, options)

        site = self._resolve_site(options)
        qs = Device.objects.filter(site=site).order_by("name")
        return self._apply_limit(list(qs), options)

    @staticmethod
    def _apply_limit(devices: list[Device], options) -> list[Device]:
        limit = options.get("limit")
        if limit and limit > 0:
            return devices[:limit]
        return devices

    def _resolve_site(self, options) -> Site:
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

        raise CommandError("Provide --device or --site/--site-id to select devices.")
