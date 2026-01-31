import logging
import random
import re
from decimal import Decimal
from pathlib import Path

import textfsm
from django.conf import settings
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
        self._is_aci = False

    def assign(self, *, return_details: bool = False):
        """
        Main entrypoint. Returns {"device": Device, "success": bool, "error": str|None}
        """
        device = None
        details = {}
        try:
            credential = self._get_ssh_credential()
            hostname_lower = (self.candidate.hostname or "").lower()
            include_config = self.include_config
            if "leaf" in hostname_lower or "spine" in hostname_lower:
                self._is_aci = True
                include_config = False
            with transaction.atomic():
                conn, device_type, version_raw = self._detect_device_type_via_version(credential)
                location_raw, parsed_version, stack_raw = self._collect_details(
                    conn, device_type, version_raw
                )
                conn.disconnect()
                stack_members_data = self._parse_stack_members(stack_raw) if stack_raw else []
                stack_count = len(stack_members_data) if stack_members_data else 0

                area_name, rack_name, requested_unit = self._parse_snmp_location(
                    location_raw
                )

                area, rack = self._resolve_area_and_rack(area_name, rack_name)
                required_units = max(1, stack_count)
                position = self._select_position(rack, requested_unit, required_units)

                model_name = self._extract_model_from_version(parsed_version)
                device_type_obj = self._resolve_device_type_obj(device_type, model_name)
                role = self._resolve_role()
                tags = self._resolve_tags()
                details = {
                    "device_type": device_type,
                    "include_config": include_config,
                    "model_name": model_name,
                    "version_raw": version_raw,
                    "parsed_version": parsed_version,
                    "location_raw": location_raw,
                    "area_name": area_name,
                    "rack_name": rack_name,
                    "requested_unit": requested_unit,
                    "stack_raw": stack_raw,
                    "stack_members": stack_members_data,
                }

                device = Device.objects.create(
                    name=self.candidate.hostname or str(self.candidate.ip_address),
                    management_ip=self.candidate.ip_address,
                    site=self.candidate.site,
                    area=area,
                    rack=rack,
                    position=position,
                    device_type=device_type_obj,
                    role=role,
                    status=DeviceStatusChoices.STATUS_ACTIVE,
                    source="discovery",
                    is_stacked=stack_count > 1,
                )
                if tags:
                    device.tags.add(*tags)
                device_name = (device.name or "").lower()
                extra_tag_names = set()
                if "mgmt" in device_name or "bmsw" in device_name:
                    extra_tag_names.add("management")
                    extra_tag_names.add("config_backup_tag")
                if extra_tag_names:
                    extra_tags = []
                    for name in extra_tag_names:
                        tag = Tag.objects.filter(name__iexact=name).first()
                        if tag:
                            extra_tags.append(tag)
                        else:
                            logger.warning("Tag '%s' not found; skipping.", name)
                    if extra_tags:
                        device.tags.add(*extra_tags)
                details["tags"] = [
                    tag.name for tag in device.tags.all().order_by("name")
                ]
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
            sync_service.sync_device(device, include_config=include_config)

            payload = {"device": device, "success": True, "error": None}
            if return_details:
                payload["details"] = details
            return payload

        except Exception as exc:
            logger.exception("Auto-assignment failed for candidate %s", self.candidate)
            payload = {"device": device, "success": False, "error": str(exc)}
            if return_details and details:
                payload["details"] = details
            return payload

    def collect_details(self):
        """
        Dry-run: collect device facts without writing to the database.
        """
        details = {}
        try:
            credential = self._get_ssh_credential()
            hostname_lower = (self.candidate.hostname or "").lower()
            include_config = self.include_config
            if "leaf" in hostname_lower or "spine" in hostname_lower:
                self._is_aci = True
                include_config = False

            conn, device_type, version_raw = self._detect_device_type_via_version(credential)
            location_raw, parsed_version, stack_raw = self._collect_details(
                conn, device_type, version_raw
            )
            conn.disconnect()
            stack_members_data = self._parse_stack_members(stack_raw) if stack_raw else []
            stack_count = len(stack_members_data) if stack_members_data else 0

            area_name, rack_name, requested_unit = self._parse_snmp_location(location_raw)

            details = {
                "device_type": device_type,
                "include_config": include_config,
                "model_name": self._extract_model_from_version(parsed_version),
                "version_raw": version_raw,
                "parsed_version": parsed_version,
                "location_raw": location_raw,
                "area_name": area_name,
                "rack_name": rack_name,
                "requested_unit": requested_unit,
                "stack_raw": stack_raw,
                "stack_members": stack_members_data,
                "stack_count": stack_count,
            }
            details["tags"] = [tag.name for tag in self._resolve_tags()]
            return {"device": None, "success": True, "error": None, "details": details}

        except Exception as exc:
            logger.exception("Auto-assignment dry-run failed for candidate %s", self.candidate)
            payload = {"device": None, "success": False, "error": str(exc)}
            if details:
                payload["details"] = details
            return payload

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

    def _parse_show_version(self, raw: str, device_type: str) -> list[dict] | None:
        if not raw:
            return None
        if self._is_aci:
            template_path = (
                Path(settings.BASE_DIR)
                / "network"
                / "parsers"
                / "textfsm"
                / "cisco_nxos_aci_show_version.textfsm"
            )
        elif device_type == 'cisco_nxos':
            template_path = (
                Path(settings.BASE_DIR)
                / "network"
                / "parsers"
                / "textfsm"
            / "cisco_nxos_show_version.textfsm"
        )
        else:  # cisco_ios
            template_path = (
                Path(settings.BASE_DIR)
                / "network"
                / "parsers"
                / "textfsm"
                / "cisco_ios_show_version.textfsm"
            )
        try:
            with open(template_path, "r", encoding="utf-8") as handle:
                fsm = textfsm.TextFSM(handle)
                results = fsm.ParseText(raw)
        except Exception as exc:
            logger.warning(
                "Could not parse NX-OS show version for %s: %s",
                self.candidate,
                exc,
            )
            return None

        if not results:
            return None
        headers = [header.lower() for header in fsm.header]
        return [dict(zip(headers, row)) for row in results]

    def _resolve_username(self, credential: SSHCredential) -> str:
        username = credential.ssh_username
        hostname = (self.candidate.hostname or "").lower()
        if "leaf" in hostname or "spine" in hostname:
            prefix = "apic#ISE\\\\"
            if not username.startswith(prefix):
                username = f"{prefix}{username}"
        return username

    def _detect_device_type_via_version(self, credential: SSHCredential) -> tuple[str, str]:
        """
        First step: determine device type using show version raw output.
        """
        params = {
            "host": str(self.candidate.ip_address),
            "username": self._resolve_username(credential),
            "password": credential.ssh_password,
            "port": credential.ssh_port,
            "timeout": 30,
            
        }
        for device_type in ('cisco_nxos', 'cisco_ios'):
            try:
                conn = ConnectHandler(**params, device_type=device_type, fast_cli=True)
                version_row = conn.send_command('show version', use_textfsm=False)
                detected_type = 'cisco_nxos' if 'NX-OS' in version_row or "NXOS" in version_row else 'cisco_ios'
                if detected_type != device_type:
                    conn.disconnect()
                    conn = ConnectHandler(**params, device_type=detected_type, fast_cli=True)
                    version_row = conn.send_command('show version', use_textfsm=False)
                if 'aci' in version_row.lower():
                    self._is_aci = True
                return conn, detected_type, version_row
            except Exception as exc:
                logger.warning(
                    "Device type detection attempt with %s failed for %s: %s",
                    device_type,
                    self.candidate,
                    exc,
                )
                continue
        raise RuntimeError(f"Could not connect to device {self.candidate} for device type detection.")
        

    def _collect_details(self, conn: ConnectHandler, device_type: str, version_raw: str
    ) -> tuple[str, dict | list | None, str | None]:
        """
        Collect SNMP location, parsed show version, and raw stack data using the correct driver.
        """

        location_raw = ""
        parsed_version = None
        stack_raw = None
       
        try:
            if device_type == 'cisco_nxos' and not self._is_aci:
                location_raw = conn.send_command("show snmp", use_textfsm=False)
            elif device_type == 'cisco_ios':
                location_raw = conn.send_command("show snmp location", use_textfsm=False)
        except Exception:
            location_raw = ""
        try:
            parsed_version = self._parse_show_version(version_raw, device_type)
        except Exception as exc:
            logger.warning("Could not collect parsed show version for %s: %s", self.candidate, exc)
            parsed_version = None

        if device_type == 'cisco_ios':
            try:
                stack_raw = conn.send_command("show switch", use_textfsm=False)
            except Exception:
                stack_raw = None

        return location_raw, parsed_version, stack_raw

    def _parse_snmp_location(self, raw: str) -> tuple[str, str, Decimal | None]:
        if self._is_aci:
            hostname_lower = (self.candidate.hostname or "").lower()
            return self._parse_aci_location_from_hostname(hostname_lower)
        lines = [ln.strip() for ln in (raw or "").splitlines() if ln.strip()]
        if not lines:
            raise RuntimeError("SNMP location empty.")
        target = lines[0]
        for line in lines:
            if "sys location" in line.lower():
                _, _, value = line.partition(":")
                if value.strip():
                    target = value.strip()
                    break
        m = self.LOCATION_RE.match(target)
        if not m:
            raise RuntimeError(f"SNMP location not in expected format: '{target}'")
        area = m.group("area")
        rack = m.group("rack")
        unit_raw = m.group("unit")
        unit = Decimal(unit_raw) if unit_raw else None
        return area, rack, unit

    def _parse_aci_location_from_hostname(
        self, hostname: str
    ) -> tuple[str, str, Decimal | None]:
        if not hostname:
            raise RuntimeError("Hostname missing for ACI location fallback.")
        base = hostname.split(".", 1)[0]
        parts = [part for part in base.split("-") if part]
        if len(parts) < 3:
            raise RuntimeError(
                f"Hostname not in expected ACI format for area/rack: '{base}'"
            )
        area = parts[1]
        rack_raw = parts[2]
        rack = f"Rack{rack_raw}"
        return area, rack, None

    def _detect_platform(self, version_raw: str) -> str:
        text = (version_raw or "").upper()
        if "NX-OS" in text:
            return DevicePlatformChoices.NX_OS
        if "IOS" in text:
            return DevicePlatformChoices.IOS
        return DevicePlatformChoices.UNKNOWN

    def _resolve_device_type_obj(self, platform: str, model_name: str | None) -> DeviceType:
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
        if "bmsw" in hostname or "mgmt" in hostname:
            tag_names.update(["management", "config_backup_tag"])
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
