import hashlib
import logging
import re
from pathlib import Path

import textfsm
from django.conf import settings
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from dcim.models import (
    Device,
    DeviceConfiguration,
    DeviceModule,
    DeviceRuntimeStatus,
    DeviceStackMember,
    DeviceType,
    Interface,
)
from dcim.choices import (
    DevicePlatformChoices,
    DeviceStackRoleChoices,
    DeviceStackStateChoices,
    InterfaceStatusChoices,
    InterfaceKindChoices,
    InterfaceModeChoices,
)
from network.adapters.netmiko import NetmikoAdapter
from network.choices import CliCommandsChoices as cli


logger = logging.getLogger(__name__)


class SyncService:

    def __init__(self, *, site):
        self.now = timezone.now()
        self.VERSION_CMD = cli.VERSION_CMD
        self.INVENTORY_CMD = cli.INVENTORY_CMD
        self.IF_STATUS_CMD = cli.IF_STATUS_CMD
        self.IF_DESC_CMD = cli.IF_DESC_CMD
        self.IF_IP_BRIEF_CMD = cli.IF_IP_BRIEF_CMD
        self.IF_TRANSCEIVER_CMD = cli.IF_TRANSCEIVER_CMD
        self.RUNNING_CONFIG_CMD = cli.RUNNING_CONFIG_CMD
        self.STACK_SWITCH_CMD = cli.STACK_SWITCH_CMD

    # =================================================
    # PUBLIC API
    # =================================================
    def sync_device(
        self,
        device: Device,
        *,
        include_config: bool = False,
        return_results: bool = False,
    ) -> dict:
        with transaction.atomic():
            runtime, _ = DeviceRuntimeStatus.objects.get_or_create(device=device)
            runtime.last_check = self.now

            is_nxos = bool(
                device.device_type
                and device.device_type.platform == DevicePlatformChoices.NX_OS
            )
            is_ios_stack = bool(
                device.device_type
                and device.device_type.platform
                in (DevicePlatformChoices.IOS, DevicePlatformChoices.IOS_XE)
            )

            portchannel_cmd = (
                cli.PORTCHANNEL_SUMMARY_NXOS_CMD
                if is_nxos
                else cli.PORTCHANNEL_SUMMARY_ISO_CMD
            )

            hostname_lower = (device.name or "").lower()
            is_aci_leaf_spine = "leaf" in hostname_lower or "spine" in hostname_lower

            try:
                results = self._collect_results_with_retry(
                    device=device,
                    include_config=include_config,
                    is_ios_stack=is_ios_stack,
                    is_nxos=is_nxos,
                    is_aci_leaf_spine=is_aci_leaf_spine,
                    portchannel_cmd=portchannel_cmd,
                )
            except Exception as exc:
                runtime.reachable_ssh = False
                runtime.save(update_fields=["reachable_ssh", "last_check"])
                if include_config:
                    self._record_config(device, success=False, error_message=str(exc))
                return {"device": device, "success": False, "error": str(exc)}

            # Mark device as reachable
            runtime.reachable_ssh = True
            runtime.save(update_fields=["reachable_ssh", "last_check"])
            # Apply retrieved data
            self._apply_version(device, runtime, results[self.VERSION_CMD])
            self._apply_inventory(device, results[self.INVENTORY_CMD])
            self._update_device_type(
                device=device,
                version_result=results[self.VERSION_CMD],
                inventory_result=results[self.INVENTORY_CMD],
            )
            if is_nxos and self.IF_TRANSCEIVER_CMD in results:
                self._apply_transceivers(device, results[self.IF_TRANSCEIVER_CMD])

            if not is_aci_leaf_spine:
                self._apply_interfaces(
                    device=device,
                    status_result=results[self.IF_STATUS_CMD],
                    desc_result=results[self.IF_DESC_CMD],
                    ip_result=results[self.IF_IP_BRIEF_CMD],
                    po_result=results[portchannel_cmd],
                )

            if include_config:
                cfg = results.get(self.RUNNING_CONFIG_CMD, {})
                self._record_config(
                    device=device,
                    success=not cfg.get("error"),
                    error_message=cfg.get("error"),
                    config_text=cfg.get("raw", "") if not cfg.get("error") else "",
                )

            if is_ios_stack and self.STACK_SWITCH_CMD in results:
                self._apply_stack_members(device, results[self.STACK_SWITCH_CMD])

            payload = {"device": device, "success": True}
            if return_results:
                payload["results"] = results
            return payload

    def _collect_results_with_retry(
        self,
        *,
        device: Device,
        include_config: bool,
        is_ios_stack: bool,
        is_nxos: bool,
        is_aci_leaf_spine: bool,
        portchannel_cmd: str,
    ) -> dict:
        last_exc = None
        for attempt in range(2):
            try:
                return self._collect_results(
                    device=device,
                    include_config=include_config,
                    is_ios_stack=is_ios_stack,
                    is_nxos=is_nxos,
                    is_aci_leaf_spine=is_aci_leaf_spine,
                    portchannel_cmd=portchannel_cmd,
                )
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "SSH sync failed for %s (attempt %s/2): %s",
                    device,
                    attempt + 1,
                    exc,
                )
        raise last_exc

    def _collect_results(
        self,
        *,
        device: Device,
        include_config: bool,
        is_ios_stack: bool,
        is_nxos: bool,
        is_aci_leaf_spine: bool,
        portchannel_cmd: str,
    ) -> dict:
        with NetmikoAdapter(device, allow_autodetect=False) as ssh:
            results = {
                self.VERSION_CMD: ssh.run_command_raw(self.VERSION_CMD),
                self.INVENTORY_CMD: ssh.run_command_raw(self.INVENTORY_CMD),
            }
            if not is_aci_leaf_spine:
                results.update(
                    {
                        self.IF_STATUS_CMD: ssh.run_command_raw(self.IF_STATUS_CMD),
                        self.IF_DESC_CMD: ssh.run_command_raw(self.IF_DESC_CMD),
                        self.IF_IP_BRIEF_CMD: ssh.run_command_raw(self.IF_IP_BRIEF_CMD),
                        portchannel_cmd: ssh.run_command_raw(portchannel_cmd),
                    }
                )
            if is_ios_stack:
                results[self.STACK_SWITCH_CMD] = ssh.run_command_raw(self.STACK_SWITCH_CMD)
            if is_nxos:
                results[self.IF_TRANSCEIVER_CMD] = ssh.run_command_raw(self.IF_TRANSCEIVER_CMD)
            if include_config:
                results[self.RUNNING_CONFIG_CMD] = ssh.run_command_raw(self.RUNNING_CONFIG_CMD)
        self._parse_results(device, results)
        return results

    # =================================================
    # VERSION / INVENTORY / CONFIG
    # =================================================
    def _apply_version(self, device: Device, runtime: DeviceRuntimeStatus, result: dict):
        parsed = result.get("parsed")
        raw = result.get("raw", "") or ""
        if self._is_aci_leaf_spine(device) and raw:
            parsed = self._parse_aci_show_version(raw) or parsed

        serial = image = None
        uptime_seconds = None

        if parsed and isinstance(parsed, list):
            entry = parsed[0]
            serial = entry.get("serial") or entry.get("serial_number")
            if isinstance(serial, list):
                serial = serial[0] if serial else ""
            image = entry.get("version") or entry.get("running_image") or entry.get("os")
            uptime_seconds = self._parse_uptime(entry.get("uptime"))
            if not uptime_seconds:
                uptime_seconds = self._uptime_from_parts(entry)
        if not uptime_seconds:
            uptime_seconds = self._parse_uptime(self._extract_uptime_line(raw))
        if not serial:
            serial = self._parse_serial_from_text(raw)
        if not image:
            image = self._parse_image_from_text(raw)

        now = self.now
        update_fields = ["last_seen"]
        device.last_seen = now

        if serial:
            device.serial_number = serial
            update_fields.append("serial_number")

        if image:
            device.image_version = image
            update_fields.append("image_version")

        if uptime_seconds:
            device.uptime = timedelta(seconds=uptime_seconds)
            device.last_reboot = now - timedelta(seconds=uptime_seconds)
            runtime.uptime = device.uptime
            runtime.save(update_fields=["uptime", "reachable_ssh", "last_check"])
            update_fields.extend(["uptime", "last_reboot"])
        else:
            runtime.save(update_fields=["reachable_ssh", "last_check"])

        device.save(update_fields=update_fields)

    def _apply_inventory(self, device: Device, result: dict):
        parsed = result.get("parsed")
        if not parsed:
            return

        seen_keys = set()
        no_serial_names = set()
        for entry in parsed:
            name = (entry.get("name") or entry.get("descr") or "Module").strip()
            serial = entry.get("sn") or entry.get("serial") or ""
            serial_value = str(serial or "").strip()
            serial_upper = serial_value.upper()
            descr = entry.get("descr") or ""
            if not serial_value or serial_upper in ("N/A", "UNKNOWN", "N") or serial_upper.startswith("UNKNOWN:"):
                no_serial_names.add(name)
                continue

            DeviceModule.objects.update_or_create(
                device=device,
                name=name,
                serial_number=serial_value,
                defaults={
                    "description": descr,
                    "vendor": None,
                },
            )
            seen_keys.add((name, serial_value))

        if seen_keys:
            keep_q = Q()
            for name, serial_value in seen_keys:
                keep_q |= Q(name=name, serial_number=serial_value)
            DeviceModule.objects.filter(device=device).filter(
                Q(serial_number__isnull=False) & ~Q(serial_number="")
            ).exclude(
                name__startswith="Transceiver "
            ).exclude(
                keep_q
            ).delete()

        if no_serial_names:
            DeviceModule.objects.filter(
                device=device,
                name__in=no_serial_names,
            ).filter(Q(serial_number__isnull=True) | Q(serial_number="")).delete()

    def _update_device_type(self, *, device: Device, version_result: dict, inventory_result: dict) -> None:
        model = self._model_from_inventory(inventory_result.get("parsed"), device.serial_number)
        if not model:
            model = self._extract_model_from_version(version_result.get("parsed"))
        if not model:
            return

        qs = DeviceType.objects.filter(model__iexact=model)
        if device.device_type and device.device_type.vendor_id:
            qs = qs.filter(vendor=device.device_type.vendor)
        device_type = qs.first()
        if not device_type:
            logger.warning("DeviceType model '%s' not found for %s", model, device)
            return
        if device.device_type_id != device_type.id:
            device.device_type = device_type
            device.save(update_fields=["device_type"])

    @staticmethod
    def _extract_model_from_version(parsed_version) -> str | None:
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
        for key in ("hardware", "model", "platform", "chassis"):
            value = entry.get(key)
            if isinstance(value, list) and value:
                return str(value[0])
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _model_from_inventory(parsed_inventory, device_serial: str | None) -> str | None:
        if not parsed_inventory:
            return None
        entries = [entry for entry in parsed_inventory if isinstance(entry, dict)]
        if not entries:
            return None

        serial_value = (device_serial or "").strip()
        if serial_value:
            for entry in entries:
                sn = str(entry.get("sn") or entry.get("serial") or "").strip()
                if sn and sn == serial_value:
                    pid = str(entry.get("pid") or entry.get("PID") or "").strip()
                    if pid:
                        return pid

        for entry in entries:
            name = str(entry.get("name") or "").strip().lower()
            if "chassis" in name or name.startswith("switch"):
                pid = str(entry.get("pid") or entry.get("PID") or "").strip()
                if pid:
                    return pid

        skip_tokens = ("STACK", "SFP", "QSFP", "FAN", "PWR", "PSU", "NM-", "TRANSCEIVER")
        for entry in entries:
            pid = str(entry.get("pid") or entry.get("PID") or "").strip()
            if not pid:
                continue
            upper = pid.upper()
            if any(token in upper for token in skip_tokens):
                continue
            return pid

        for entry in entries:
            pid = str(entry.get("pid") or entry.get("PID") or "").strip()
            if pid:
                return pid
        return None

    def _apply_transceivers(self, device: Device, result: dict):
        entries = self._parse_transceiver_entries(result)
        seen_names = set()
        for entry in entries:
            name = entry.get("name")
            if not name:
                continue
            seen_names.add(name)
            DeviceModule.objects.update_or_create(
                device=device,
                name=name,
                defaults={
                    "description": entry.get("description"),
                    "serial_number": entry.get("serial"),
                    "vendor": None,
                },
            )
        if seen_names:
            DeviceModule.objects.filter(
                device=device,
                name__startswith="Transceiver ",
            ).exclude(name__in=seen_names).delete()

    def _is_aci_leaf_spine(self, device: Device) -> bool:
        hostname = (device.name or "").lower()
        return "leaf" in hostname or "spine" in hostname

    def _parse_results(self, device: Device, results: dict) -> None:
        for command, result in results.items():
            if not isinstance(result, dict):
                continue
            raw = result.get("raw") or ""
            if not raw:
                continue
            template_name = self._template_for_command(device, command)
            if not template_name:
                continue
            parsed = self._parse_with_textfsm(raw, template_name, device=device)
            if parsed:
                result["parsed"] = parsed

    def _template_for_command(self, device: Device, command: str) -> str | None:
        platform = device.device_type.platform if device.device_type else None
        if platform in (DevicePlatformChoices.IOS, DevicePlatformChoices.IOS_XE):
            templates = {
                self.VERSION_CMD: "cisco_ios_show_version.textfsm",
                self.INVENTORY_CMD: "cisco_ios_show_inventory.textfsm",
                self.IF_STATUS_CMD: "cisco_ios_show_interface_status.textfsm",
                self.IF_DESC_CMD: "cisco_ios_show_interface_description.textfsm",
                self.IF_IP_BRIEF_CMD: "cisco_ios_show_ip_interface_brief.textfsm",
                cli.PORTCHANNEL_SUMMARY_ISO_CMD: "cisco_ios_show_etherchannel_summary.textfsm",
            }
            return templates.get(command)
        if platform == DevicePlatformChoices.NX_OS:
            if self._is_aci_leaf_spine(device) and command == self.VERSION_CMD:
                return None
            templates = {
                self.VERSION_CMD: "cisco_nxos_show_version.textfsm",
                self.INVENTORY_CMD: "cisco_nxos_show_inventory.textfsm",
                self.IF_STATUS_CMD: "cisco_nxos_show_interface_status.textfsm",
                self.IF_DESC_CMD: "cisco_nxos_show_interface_description.textfsm",
                self.IF_IP_BRIEF_CMD: "cisco_nxos_show_ip_interface_brief.textfsm",
                cli.PORTCHANNEL_SUMMARY_NXOS_CMD: "cisco_nxos_show_port-channel_summary.textfsm",
                self.IF_TRANSCEIVER_CMD: "cisco_nxos_show_interface_transceiver.textfsm",
            }
            return templates.get(command)
        return None

    def _parse_with_textfsm(self, raw: str, template_name: str, *, device: Device) -> list[dict] | None:
        template_path = (
            Path(settings.BASE_DIR)
            / "network"
            / "parsers"
            / "textfsm"
            / template_name
        )
        try:
            with open(template_path, "r", encoding="utf-8") as handle:
                fsm = textfsm.TextFSM(handle)
                results = fsm.ParseText(raw)
        except Exception as exc:
            logger.warning(
                "TextFSM parse failed for %s (%s): %s",
                device,
                template_name,
                exc,
            )
            return None

        if not results:
            return None
        headers = [header.lower() for header in fsm.header]
        return [dict(zip(headers, row)) for row in results]

    def _parse_aci_show_version(self, raw: str) -> list[dict] | None:
        template_path = (
            Path(settings.BASE_DIR)
            / "network"
            / "parsers"
            / "textfsm"
            / "cisco_nxos_aci_show_version.textfsm"
        )
        try:
            with open(template_path, "r", encoding="utf-8") as handle:
                fsm = textfsm.TextFSM(handle)
                results = fsm.ParseText(raw)
        except Exception as exc:
            logger.warning("ACI show version parse failed: %s", exc)
            return None

        if not results:
            return None
        headers = [header.lower() for header in fsm.header]
        return [dict(zip(headers, row)) for row in results]

    def _parse_transceiver_entries(self, result: dict) -> list[dict]:
        parsed = result.get("parsed")
        if parsed:
            entries = self._parse_transceivers_from_parsed(parsed)
            if entries:
                return entries
        raw = result.get("raw", "") or ""
        return self._parse_transceivers_from_raw(raw)

    def _parse_transceivers_from_parsed(self, parsed) -> list[dict]:
        entries: list[dict] = []
        if isinstance(parsed, dict):
            parsed = [parsed]
        if not isinstance(parsed, list):
            return entries

        for entry in parsed:
            if not isinstance(entry, dict):
                continue
            if not self._is_transceiver_present(entry):
                continue
            interface = self._first_match(
                entry,
                ["interface", "port", "intf", "interface_name"],
            )
            if not interface:
                name_value = entry.get("name") if isinstance(entry.get("name"), str) else ""
                if self._looks_like_interface(name_value):
                    interface = name_value
            module_type = self._first_match(
                entry,
                ["type", "module_type", "transceiver", "product_id", "pid"],
            )
            serial = self._first_match(
                entry,
                ["serial", "serial_number", "sn"],
            )
            if not self._has_valid_serial(serial):
                continue
            vendor_name = entry.get("name") if isinstance(entry.get("name"), str) else ""
            part_number = self._first_match(
                entry,
                ["part_number", "part", "partnum", "pn"],
            )

            name = self._format_transceiver_name(interface, module_type, serial)
            description = self._format_transceiver_description(
                module_type, vendor_name, part_number
            )
            entries.append(
                {
                    "name": name,
                    "description": description,
                    "serial": serial,
                }
            )
        return entries

    def _parse_transceivers_from_raw(self, raw: str) -> list[dict]:
        entries: list[dict] = []
        current = None

        for line in raw.splitlines():
            if not line.strip():
                continue
            if line.startswith(" ") or line.startswith("\t"):
                if not current:
                    continue
                normalized = line.strip()
                lower = normalized.lower()
                if "transceiver is present" in lower:
                    current["present"] = True
                elif "transceiver is not present" in lower:
                    current["present"] = False
                if "type is" in lower:
                    current["type"] = normalized.split("type is", 1)[1].strip()
                elif "serial number is" in lower:
                    current["serial"] = normalized.split("serial number is", 1)[1].strip()
                elif "name is" in lower:
                    current["vendor"] = normalized.split("name is", 1)[1].strip()
                elif "part number is" in lower:
                    current["part"] = normalized.split("part number is", 1)[1].strip()
                continue

            if self._looks_like_interface(line.strip()):
                current = {
                    "interface": line.strip(),
                    "present": None,
                }
                entries.append(current)

        if not entries and raw:
            for line in raw.splitlines():
                if not line.strip():
                    continue
                if line.lower().startswith("interface"):
                    continue
                if not self._looks_like_interface(line.strip()):
                    continue
                parts = [p for p in re.split(r"\s{2,}", line.strip()) if p]
                if not parts:
                    continue
                if any("not present" in part.lower() for part in parts):
                    continue
                current = {
                    "interface": parts[0],
                    "type": parts[1] if len(parts) > 1 else "",
                    "vendor": parts[2] if len(parts) > 2 else "",
                    "part": parts[3] if len(parts) > 3 else "",
                    "serial": parts[4] if len(parts) > 4 else "",
                    "present": None,
                }
                entries.append(current)

        results = []
        for entry in entries:
            if entry.get("present") is False:
                continue
            interface = entry.get("interface")
            module_type = entry.get("type")
            serial = entry.get("serial")
            if not self._has_valid_serial(serial):
                continue
            vendor_name = entry.get("vendor")
            part_number = entry.get("part")
            name = self._format_transceiver_name(interface, module_type, serial)
            description = self._format_transceiver_description(
                module_type, vendor_name, part_number
            )
            results.append(
                {
                    "name": name,
                    "description": description,
                    "serial": serial,
                }
            )
        return results

    def _apply_stack_members(self, device: Device, result: dict):
        members = self._parse_stack_members(result)
        seen_numbers = []
        for member in members:
            switch_number = member.get("switch_number")
            if switch_number is None:
                continue
            seen_numbers.append(switch_number)
            DeviceStackMember.objects.update_or_create(
                device=device,
                switch_number=switch_number,
                defaults={
                    "role": member.get("role", DeviceStackRoleChoices.UNKNOWN),
                    "mac_address": member.get("mac_address", ""),
                    "priority": member.get("priority"),
                    "version": member.get("version"),
                    "state": member.get("state", DeviceStackStateChoices.UNKNOWN),
                },
            )
        if seen_numbers:
            device.stack_members.exclude(switch_number__in=seen_numbers).delete()
        # Update device stacked flag and rack occupancy
        is_stacked = len(seen_numbers) > 1
        if device.is_stacked != is_stacked:
            device.is_stacked = is_stacked
            device.save(update_fields=["is_stacked"])
        if device.rack_id:
            from dcim.models.device import update_rack_occupied_units
            update_rack_occupied_units(device.rack_id)

    def _parse_stack_members(self, result: dict) -> list[dict]:
        parsed = result.get("parsed")
        entries: list[dict] = []
        if parsed:
            entries = self._parse_stack_from_parsed(parsed)
        if not entries:
            raw = result.get("raw", "") or ""
            entries = self._parse_stack_from_raw(raw)
        return entries

    def _parse_stack_from_parsed(self, parsed) -> list[dict]:
        entries: list[dict] = []
        if isinstance(parsed, dict):
            parsed = [parsed]
        if not isinstance(parsed, list):
            return entries
        for entry in parsed:
            if not isinstance(entry, dict):
                continue
            switch_num = entry.get("switch") or entry.get("switch_number")
            try:
                switch_num = int(str(switch_num).strip())
            except (TypeError, ValueError):
                continue
            role = self._normalize_stack_role(entry.get("role"))
            state = self._normalize_stack_state(entry.get("state"))
            mac = entry.get("mac") or entry.get("mac_address") or ""
            priority = entry.get("priority")
            try:
                priority = int(priority) if priority is not None else None
            except (TypeError, ValueError):
                priority = None
            entries.append(
                {
                    "switch_number": switch_num,
                    "role": role,
                    "mac_address": mac,
                    "priority": priority,
                    "version": entry.get("version"),
                    "state": state,
                }
            )
        return entries

    def _parse_stack_from_raw(self, raw: str) -> list[dict]:
        entries: list[dict] = []
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

    def _format_transceiver_name(self, interface: str | None, module_type: str | None, serial: str | None) -> str:
        if interface:
            return f"Transceiver {interface}"
        if module_type:
            return f"Transceiver {module_type}"
        if serial:
            return f"Transceiver {serial}"
        return "Transceiver"

    def _format_transceiver_description(
        self,
        module_type: str | None,
        vendor_name: str | None,
        part_number: str | None,
    ) -> str | None:
        parts = []
        if module_type:
            parts.append(module_type)
        if vendor_name and vendor_name not in parts:
            parts.append(vendor_name)
        if part_number:
            parts.append(f"PN {part_number}")
        return " / ".join(parts) if parts else None

    def _first_match(self, entry: dict, keys: list[str]) -> str | None:
        for key in keys:
            value = entry.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _looks_like_interface(self, value: str | None) -> bool:
        if not value:
            return False
        return bool(re.match(r"^[A-Za-z]+[0-9/.-]+$", value))

    def _is_transceiver_present(self, entry: dict) -> bool:
        for key in ["present", "transceiver", "status", "state"]:
            value = entry.get(key)
            if isinstance(value, str):
                value_lower = value.lower()
                if "not present" in value_lower or "absent" in value_lower or value_lower == "no":
                    return False
                if "present" in value_lower or value_lower in ("yes", "true"):
                    return True
            if isinstance(value, bool):
                return value
        return True

    @staticmethod
    def _has_valid_serial(serial: str | None) -> bool:
        serial_value = str(serial or "").strip()
        if not serial_value:
            return False
        serial_upper = serial_value.upper()
        if serial_upper in ("N/A", "UNKNOWN", "N"):
            return False
        if serial_upper.startswith("UNKNOWN:"):
            return False
        return True

    def _record_config(
        self,
        device: Device,
        *,
        success: bool,
        error_message: str | None = None,
        config_text: str = "",
    ):
        previous = device.configs.order_by("-collected_at").first()
        payload = config_text or ""
        config_hash = hashlib.sha256(payload.encode()).hexdigest()

        DeviceConfiguration.objects.create(
            device=device,
            config_text=payload,
            source="ssh",
            success=success,
            error_message=error_message,
            config_hash=config_hash,
            previous=previous,
        )

    # =================================================
    # INTERFACE NORMALIZATION PIPELINE
    # =================================================
    def _apply_interfaces(self, *, device, status_result, desc_result, ip_result, po_result):
        status_map = {}
        desc_map = {}
        ip_map = {}
        ip_seen = {}
        lag_map = {}

        # ---- descriptions ----
        for e in desc_result.get("parsed", []) or []:
            name = self._normalize_iface(e.get("port") or e.get("interface"))
            if not name:
                continue
            if "Vl" in name:
                continue  # Skip VLAN interfaces here; handled via ip brief
            desc_map[name] = (e.get("description") or "").strip()

        # ---- status ----
        for e in status_result.get("parsed", []) or []:
            name = self._normalize_iface(e.get("port") or e.get("interface"))
            if not name:
                continue
            vlan_raw = str(
                e.get("vlan") or e.get("vlan_id") or e.get("VLAN") or ""
            ).strip()
            speed_raw = str(e.get("speed") or "").strip()
            duplex_raw = str(e.get("duplex") or "").strip()
            status_map[name] = {
                "status": (e.get("status") or "").lower(),
                "vlan": vlan_raw.lower(),
                "vlan_raw": vlan_raw or None,
                "speed": self._parse_speed(speed_raw),
                "speed_mode": speed_raw or None,
                "duplex": duplex_raw or None,
            }

        # ---- ip brief ----
        for e in ip_result.get("parsed", []) or []:
            name = self._normalize_iface(e.get("intf") or e.get("interface"))
            if not name:
                continue
            ip = e.get("ipaddr") or e.get("ip_address")
            status = (e.get("status") or "").lower()
            proto = (e.get("proto") or "").lower()
            ip_value = (ip or "").strip()
            if ip_value and ip_value.lower() != "unassigned":
                ip_map[name] = {
                    "ip": ip_value,
                    "status": status,   # interface status
                    "proto": proto,     # protocol status
                }
                ip_seen[name] = ip_map[name]

        # ---- port-channel ----
        for e in po_result.get("parsed", []) or []:
            po_raw = (
                e.get("port_channel")
                or e.get("bundle_name")
                or e.get("bundle")
                or e.get("portchannel")
            )
            if isinstance(po_raw, str):
                po_raw = po_raw.split("(")[0]
            po = self._normalize_iface(po_raw)
            if not po:
                continue
            members = []
            if isinstance(e.get("interfaces"), str):
                members = e.get("interfaces").split()
            elif isinstance(e.get("member_interface"), list):
                members = e.get("member_interface")
            elif isinstance(e.get("member_interface"), str):
                members = [e.get("member_interface")]
            for m in members:
                member_name = m.split("(")[0] if isinstance(m, str) else ""
                member = self._normalize_iface(member_name)
                if member:
                    lag_map[member] = po

                
        # ---- create all interfaces ----
        all_names = set(status_map) | set(ip_seen) | set(lag_map.values())
        iface_objs = {
            name: Interface.objects.get_or_create(device=device, name=name)[0]
            for name in all_names
        }

        # ---- kind ----
        for name, iface in iface_objs.items():
            iface.kind = self._infer_kind(name)
            iface.save(update_fields=["kind"])

        # ---- mode ----
        for name, iface in iface_objs.items():
            vlan = status_map.get(name, {}).get("vlan")
            if iface.kind in {
                InterfaceKindChoices.SVI,
                InterfaceKindChoices.LOOPBACK,
                InterfaceKindChoices.TUNNEL,
            }:
                iface.mode = InterfaceModeChoices.L3
            elif vlan:
                iface.mode = InterfaceModeChoices.L2
            elif name in ip_map:
                iface.mode = InterfaceModeChoices.L3
            iface.save(update_fields=["mode"])

        # ---- lag binding ----
        for member_name, po_name in lag_map.items():
            member = iface_objs.get(member_name)
            po = iface_objs.get(po_name)
            if member and po:
                member.lag = po
                member.lag_mode = "active"
                member.save(update_fields=["lag", "lag_mode"])

        # ---- status / description ----
        for name, iface in iface_objs.items():
            update_fields = []
            if name in desc_map:
                iface.description = desc_map.get(name, "") or ""
                update_fields.append("description")

            if name in status_map:
                ifc = status_map[name]
                mapped_status = self._map_status(ifc.get("status"))
                iface.status = mapped_status
                iface.speed = ifc.get("speed")
                iface.speed_mode = ifc.get("speed_mode")
                iface.duplex = ifc.get("duplex")
                iface.vlan_raw = ifc.get("vlan_raw")
                iface.is_trunk = "trunk" in (ifc.get("vlan") or "")
                update_fields.extend(
                    [
                        "status",
                        "speed",
                        "speed_mode",
                        "duplex",
                        "vlan_raw",
                        "is_trunk",
                    ]
                )
            else:
                mapped_status = None

            ip_data = ip_seen.get(name)
            if (
                ip_data
                and (
                    name not in status_map
                    or mapped_status == InterfaceStatusChoices.UNKNOWN
                )
            ):
                ip_status = self._map_status_from_ip_brief(
                    ip_data.get("status"),
                    ip_data.get("proto"),
                )
                if ip_status:
                    iface.status = ip_status
                    if "status" not in update_fields:
                        update_fields.append("status")

            if update_fields:
                iface.save(update_fields=update_fields)

        # ---- TEMP: IP on interface (pre-IPAM) ----
        for name, ip_data in ip_seen.items():
            iface = iface_objs.get(name)
            if iface is None:
                continue
            ip_value = ip_data.get("ip")
            if ip_value and str(ip_value).lower() != "unassigned":
                iface.ip_address = ip_value
            else:
                iface.ip_address = None
            iface.save(update_fields=["ip_address"])

    # =================================================
    # HELPERS
    # =================================================
    @staticmethod
    def _normalize_iface(name: str) -> str:
        if not name:
            return ""
        n = name.strip()
        replacements = {
            r"^Port-channel": "Po",
            r"^GigabitEthernet": "Gi",
            r"^TenGigabitEthernet": "Te",
            r"^FortyGigabitEthernet": "Fo",
            r"^TwentyFiveGigE": "Tw",
            r"^HundredGigE": "Hu",
            r"^Ethernet": "Eth",
        }
        for pattern, short in replacements.items():
            n = re.sub(pattern, short, n, flags=re.IGNORECASE)
        return n

    @staticmethod
    def _infer_kind(name: str) -> str:
        n = name.lower()
        if n.startswith("po"):
            return InterfaceKindChoices.PORT_CHANNEL
        if n.startswith("vlan"):
            return InterfaceKindChoices.SVI
        if n.startswith("loopback"):
            return InterfaceKindChoices.LOOPBACK
        if n.startswith("tunnel"):
            return InterfaceKindChoices.TUNNEL
        return InterfaceKindChoices.PHYSICAL

    @staticmethod
    def _parse_speed(speed_raw):
        if not speed_raw:
            return None
        s = str(speed_raw).lower()
        if s in {"auto", "a-auto", "unknown", "n/a"}:
            return None
        m = re.search(r"(\d+)\s*(g|m)?", s)
        if not m:
            return None
        value = int(m.group(1))
        return value * 1000 if m.group(2) == "g" else value

    @staticmethod
    def _map_status(status_raw: str):
        if not status_raw:
            return InterfaceStatusChoices.DOWN
        if "up" in status_raw:
            return InterfaceStatusChoices.UP
        if "notconnec" in status_raw:
            return InterfaceStatusChoices.NOTCONNECTED
        if "err" in status_raw:
            return InterfaceStatusChoices.ERR_DISABLED
        if "disabled" in status_raw:
            return InterfaceStatusChoices.DISABLED
        if "connected" in status_raw:
            return InterfaceStatusChoices.CONNECTED
        if "xcvrabsen" in status_raw:
            return InterfaceStatusChoices.XCVR_ABSENCE
        if "inactive" in status_raw:
            return InterfaceStatusChoices.INACTIVE
        return InterfaceStatusChoices.UNKNOWN

    @staticmethod
    def _map_status_from_ip_brief(status_raw: str, proto_raw: str):
        status = (status_raw or "").strip().lower()
        proto = (proto_raw or "").strip().lower()
        if status == "up" and proto == "up":
            return InterfaceStatusChoices.UP
        if status in {"administratively down", "admin down", "down"} or proto == "down":
            return InterfaceStatusChoices.DOWN
        return InterfaceStatusChoices.UNKNOWN

    @staticmethod
    def _parse_serial_from_text(raw: str):
        m = re.search(r"[Ss]erial [Nn]umber\s*[:#]?\s*([A-Z0-9\-]+)", raw or "")
        return m.group(1) if m else ""

    @staticmethod
    def _parse_uptime(uptime_str):
        if not uptime_str:
            return None
        total = 0
        units = {
            "year": 365 * 24 * 3600,
            "week": 7 * 24 * 3600,
            "day": 24 * 3600,
            "hour": 3600,
            "minute": 60,
            "second": 1,
        }
        for k, mult in units.items():
            m = re.search(rf"(\d+)\s+{k}", uptime_str, re.I)
            if m:
                total += int(m.group(1)) * mult
        return total or None

    @staticmethod
    def _uptime_from_parts(entry: dict) -> int | None:
        total = 0
        parts = {
            "uptime_years": 365 * 24 * 3600,
            "uptime_weeks": 7 * 24 * 3600,
            "uptime_days": 24 * 3600,
            "uptime_hours": 3600,
            "uptime_minutes": 60,
            "uptime_seconds": 1,
        }
        for key, mult in parts.items():
            value = entry.get(key)
            if value is None or value == "":
                continue
            try:
                total += int(value) * mult
            except (TypeError, ValueError):
                continue
        return total or None

    @staticmethod
    def _extract_uptime_line(raw: str):
        for line in (raw or "").splitlines():
            if "uptime is" in line.lower():
                return line
        return ""

    @staticmethod
    def _parse_image_from_text(raw: str):
        m = re.search(r"\bVersion\s+([0-9A-Za-z().-]+)", raw or "")
        return m.group(1) if m else None

    @staticmethod
    def _normalize_stack_role(role: str | None) -> str:
        value = (role or "").strip().lower()
        if value in {"active"}:
            return DeviceStackRoleChoices.ACTIVE
        if value in {"standby"}:
            return DeviceStackRoleChoices.STANDBY
        if value in {"master"}:
            return DeviceStackRoleChoices.MASTER
        if value in {"member"}:
            return DeviceStackRoleChoices.MEMBER
        return DeviceStackRoleChoices.UNKNOWN

    @staticmethod
    def _normalize_stack_state(state: str | None) -> str:
        value = (state or "").strip().lower()
        if value == "ready":
            return DeviceStackStateChoices.READY
        if "provision" in value:
            return DeviceStackStateChoices.PROVISIONED
        if "remove" in value:
            return DeviceStackStateChoices.REMOVED
        return DeviceStackStateChoices.UNKNOWN
