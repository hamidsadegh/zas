import logging
import random
import re
from decimal import Decimal

from django.db import transaction

from netmiko import ConnectHandler

from accounts.models.credentials import SSHCredential
from automation.choices import NETMIKO_PLATFORM_MAP
from dcim.choices import (
    DevicePlatformChoices,
    DeviceStatusChoices,
)
from dcim.models import (
    Area,
    Device,
    DeviceRole,
    DeviceType,
    DeviceStackMember,
    Rack,
    Tag,
    Vendor,
)
from network.models.discovery import DiscoveryCandidate
from network.services.sync_service import SyncService


logger = logging.getLogger(__name__)


class AutoAssignmentService:
    """
    Assign a discovered candidate into DCIM as a Device using deterministic rules.
    """

    LOCATION_RE = re.compile(
        r"^(?P<area>\S+)\s+(?P<rack>\S+)(?:\s+U(?P<unit>\d+(?:\.\d+)?))?$",
        re.IGNORECASE,
    )

    def __init__(self, candidate: DiscoveryCandidate, include_config: bool = True):
        self.candidate = candidate
        self.include_config = include_config

    def assign(self):
        """
        Main entrypoint. Returns {"device": Device, "success": bool, "error": str|None}
        """
        device = None
        try:
            credential = self._get_ssh_credential()
            with transaction.atomic():
                platform, version_raw = self._detect_platform_via_version(credential)
                location_raw, parsed_version, stack_raw = self._collect_details_with_driver(
                    platform, credential
                )
                stack_members_data = self._parse_stack_members(stack_raw) if stack_raw else []
                stack_count = len(stack_members_data) if stack_members_data else 0

                area_name, rack_name, requested_unit = self._parse_snmp_location(
                    location_raw
                )

                area, rack = self._resolve_area_and_rack(area_name, rack_name)
                required_units = max(1, stack_count)
                position = self._select_position(rack, requested_unit, required_units)

                model_name = self._extract_model_from_version(parsed_version)
                device_type = self._resolve_device_type(platform, model_name)
                role = self._resolve_role()
                tags = self._resolve_tags()

                device = Device.objects.create(
                    name=self.candidate.hostname or str(self.candidate.ip_address),
                    management_ip=self.candidate.ip_address,
                    site=self.candidate.site,
                    area=area,
                    rack=rack,
                    position=position,
                    device_type=device_type,
                    role=role,
                    status=DeviceStatusChoices.STATUS_ACTIVE,
                    source="discovery",
                    is_stacked=stack_count > 1,
                )
                if tags:
                    device.tags.add(*tags)
                if stack_members_data:
                    DeviceStackMember.objects.filter(device=device).delete()
                    DeviceStackMember.objects.bulk_create(
                        [
                            DeviceStackMember(
                                device=device,
                                switch_number=entry["switch_number"],
                                role=entry.get("role") or "unknown",
                                mac_address=entry.get("mac_address") or "",
                                priority=entry.get("priority"),
                                version=entry.get("version"),
                                state=entry.get("state") or "unknown",
                            )
                            for entry in stack_members_data
                        ]
                    )
                    # Refresh rack occupancy to reflect multi-unit stacks
                    from dcim.models.device import update_rack_occupied_units
                    update_rack_occupied_units(rack.id)

                # Mark candidate as handled
                self.candidate.accepted = True
                self.candidate.classified = True
                self.candidate.save(update_fields=["accepted", "classified"])

            # Run a sync after creation (outside transaction to avoid long locks)
            sync_service = SyncService(site=device.site)
            sync_service.sync_device(device, include_config=self.include_config)

            return {"device": device, "success": True, "error": None}

        except Exception as exc:
            logger.exception("Auto-assignment failed for candidate %s", self.candidate)
            return {"device": device, "success": False, "error": str(exc)}

    # -------------------------------------------------
    # Resolution helpers
    # -------------------------------------------------
    def _get_ssh_credential(self) -> SSHCredential:
        credential = (
            SSHCredential.objects.select_related("site")
            .filter(site=self.candidate.site)
            .first()
        )
        if not credential:
            raise RuntimeError(
                f"No SSH credentials configured for site '{self.candidate.site}'."
            )
        return credential

    def _detect_platform_via_version(self, credential: SSHCredential) -> tuple[str, str]:
        """
        First step: determine platform using show version raw output.
        """
        params = {
            "device_type": "cisco_nxos",  # tolerant for IOS/IOS-XE/NX-OS
            "host": str(self.candidate.ip_address),
            "username": credential.ssh_username,
            "password": credential.ssh_password,
            "port": credential.ssh_port,
            "timeout": 30,
        }
        with ConnectHandler(**params) as conn:
            version_raw = conn.send_command("show version", use_textfsm=False)
        if not version_raw:
            raise RuntimeError("Could not read 'show version' from device.")
        platform = self._detect_platform(version_raw)
        return platform, version_raw

    def _collect_details_with_driver(
        self, platform: str, credential: SSHCredential
    ) -> tuple[str, dict | list | None, str | None]:
        """
        Collect SNMP location, parsed show version, and raw stack data using the correct driver.
        """
        driver = NETMIKO_PLATFORM_MAP.get(platform, "autodetect")
        params = {
            "device_type": driver,
            "host": str(self.candidate.ip_address),
            "username": credential.ssh_username,
            "password": credential.ssh_password,
            "port": credential.ssh_port,
            "timeout": 30,
        }
        location_raw = ""
        parsed_version = None
        stack_raw = None
        with ConnectHandler(**params) as conn:
            try:
                location_raw = conn.send_command("show snmp location", use_textfsm=False)
            except Exception:
                location_raw = ""
            if not location_raw:
                try:
                    location_raw = conn.send_command("show snmp", use_textfsm=False)
                except Exception:
                    location_raw = ""
            try:
                parsed_version = conn.send_command("show version", use_textfsm=True)
            except Exception as exc:
                logger.warning("Could not collect parsed show version for %s: %s", self.candidate, exc)
            if platform in (DevicePlatformChoices.IOS, DevicePlatformChoices.IOS_XE, DevicePlatformChoices.NX_OS):
                try:
                    stack_raw = conn.send_command("show switch", use_textfsm=False)
                except Exception:
                    stack_raw = None

        if not location_raw:
            raise RuntimeError("Could not read SNMP location from device.")

        return location_raw, parsed_version, stack_raw

    def _parse_snmp_location(self, raw: str) -> tuple[str, str, Decimal | None]:
        lines = [ln.strip() for ln in (raw or "").splitlines() if ln.strip()]
        if not lines:
            raise RuntimeError("SNMP location empty.")
        target = lines[0]
        m = self.LOCATION_RE.match(target)
        if not m:
            raise RuntimeError(f"SNMP location not in expected format: '{target}'")
        area = m.group("area")
        rack = m.group("rack")
        unit_raw = m.group("unit")
        unit = Decimal(unit_raw) if unit_raw else None
        return area, rack, unit

    def _detect_platform(self, version_raw: str) -> str:
        text = (version_raw or "").upper()
        if "NX-OS" in text:
            return DevicePlatformChoices.NX_OS
        if "IOS" in text:
            return DevicePlatformChoices.IOS
        return DevicePlatformChoices.UNKNOWN

    def _resolve_device_type(self, platform: str, model_name: str | None) -> DeviceType:
        vendor = Vendor.objects.filter(name__iexact="Cisco").first()
        if not vendor:
            raise RuntimeError("Vendor 'Cisco' not found; create it before auto-assignment.")
        model_value = model_name or "Unknown (auto)"
        existing = DeviceType.objects.filter(vendor=vendor, model__iexact=model_value).first()
        if not existing:
            raise RuntimeError(
                f"DeviceType '{model_value}' for vendor '{vendor.name}' not found; create it before auto-assignment."
            )
        # Reuse existing type; do not mutate platform to avoid unexpected changes.
        return existing

    def _resolve_role(self) -> DeviceRole:
        role, _ = DeviceRole.objects.get_or_create(
            name="Access Switch",
            defaults={"description": "Auto-assigned default role"},
        )
        return role

    def _resolve_area_and_rack(self, area_name: str, rack_name: str) -> tuple[Area, Rack]:
        try:
            area = Area.objects.get(site=self.candidate.site, name__iexact=area_name)
        except Area.DoesNotExist:
            raise RuntimeError(f"Area '{area_name}' not found in site '{self.candidate.site}'.")

        try:
            rack = Rack.objects.get(area=area, name__iexact=rack_name)
        except Rack.DoesNotExist:
            raise RuntimeError(
                f"Rack '{rack_name}' not found in area '{area_name}' for site '{self.candidate.site}'."
            )
        return area, rack

    def _select_position(self, rack: Rack, requested_unit: Decimal | None, required_units: int = 1) -> Decimal | None:
        occupied = set()
        for pos in rack.occupied_units or []:
            try:
                occupied.add(int(Decimal(str(pos))))
            except Exception:
                continue

        if requested_unit:
            start = int(requested_unit)
            if all((start + offset) not in occupied for offset in range(required_units)):
                return requested_unit

        max_u = rack.u_height or 42
        candidates = []
        for start in range(1, max_u - required_units + 2):
            if all((start + offset) not in occupied for offset in range(required_units)):
                candidates.append(start)

        if not candidates:
            raise RuntimeError(f"No free rack units available in rack '{rack}' for required size {required_units}.")
        choice = random.choice(candidates)
        return Decimal(choice)

    def _resolve_tags(self) -> list[Tag]:
        hostname = (self.candidate.hostname or "").lower()
        tag_names = set(["reachability_check_tag", "discovered-new"])
        if "bcsw" in hostname:
            tag_names.update(["campus", "config_backup_tag"])
        if "bpp" in hostname:
            tag_names.update(["post_pro", "config_backup_tag"])
        if "leaf" in hostname or "spine" in hostname:
            tag_names.add("aci_fabric")

        tags = []
        for name in tag_names:
            tag = Tag.objects.filter(name__iexact=name).first()
            if tag:
                tags.append(tag)
            else:
                logger.warning("Tag '%s' not found; skipping.", name)
        return tags

    @staticmethod
    def _extract_model_from_version(parsed_version) -> str | None:
        """
        Try to pull a model identifier from textfsm parsed show version output.
        Handles common IOS/NX-OS structures.
        """
        if not parsed_version:
            return None
        data = parsed_version
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list) or not data:
            return None
        entry = data[0]
        if not isinstance(entry, dict):
            return None
        # Common keys
        for key in ("hardware", "model", "platform", "chassis"):
            value = entry.get(key)
            if isinstance(value, list) and value:
                return str(value[0])
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _parse_stack_members(self, raw: str | None) -> list[dict]:
        entries: list[dict] = []
        if not raw:
            return entries
        for line in raw.splitlines():
            if not line.strip():
                continue
            if "switch#" in line.lower() or line.startswith("---"):
                continue
            m = re.match(
                r"^\*?\s*(\d+)\s+([A-Za-z]+)\s+([0-9a-fA-F.]+)\s+(\d+)\s+(\S+)\s+([A-Za-z]+)",
                line.strip(),
            )
            if not m:
                continue
            switch_number = int(m.group(1))
            role_raw = m.group(2)
            mac = m.group(3)
            try:
                priority = int(m.group(4))
            except ValueError:
                priority = None
            version = m.group(5)
            state_raw = m.group(6)
            entries.append(
                {
                    "switch_number": switch_number,
                    "role": self._normalize_stack_role(role_raw),
                    "mac_address": mac,
                    "priority": priority,
                    "version": version,
                    "state": self._normalize_stack_state(state_raw),
                }
            )
        return entries

    @staticmethod
    def _normalize_stack_role(role: str | None) -> str:
        value = (role or "").strip().lower()
        if value in {"active"}:
            return "active"
        if value in {"standby"}:
            return "standby"
        if value in {"master"}:
            return "master"
        if value in {"member"}:
            return "member"
        return "unknown"

    @staticmethod
    def _normalize_stack_state(state: str | None) -> str:
        value = (state or "").strip().lower()
        if value == "ready":
            return "ready"
        if "provision" in value:
            return "provisioned"
        if "remove" in value:
            return "removed"
        return "unknown"
