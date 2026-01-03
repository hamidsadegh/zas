import hashlib
import re
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from dcim.models import (
    Device,
    DeviceConfiguration,
    DeviceModule,
    DeviceRuntimeStatus,
    Interface,
    VLAN,
)
from dcim.choices import InterfaceStatusChoices
from network.adapters.netmiko import NetmikoAdapter


class SyncService:
    VERSION_CMD = "show version"
    INVENTORY_CMD = "show inventory"
    IF_STATUS_CMD = "show interfaces status"
    IF_IP_BRIEF_CMD = "show ip interface brief"
    RUNNING_CONFIG_CMD = "show running-config"

    def __init__(self, *, site):
        self.site = site
        self.now = timezone.now()

    # -------------------------------------------------
    # Public API
    # -------------------------------------------------
    def sync_device(self, device: Device, *, include_config: bool = True) -> dict:
        with transaction.atomic():
            runtime, _ = DeviceRuntimeStatus.objects.get_or_create(device=device)
            runtime.last_check = self.now

            try:
                with NetmikoAdapter(device) as ssh:
                    results = {
                        self.VERSION_CMD: ssh.run_command(self.VERSION_CMD),
                        self.INVENTORY_CMD: ssh.run_command(self.INVENTORY_CMD),
                        self.IF_STATUS_CMD: ssh.run_command(self.IF_STATUS_CMD),
                        self.IF_IP_BRIEF_CMD: ssh.run_command(self.IF_IP_BRIEF_CMD),
                    }
                    if include_config:
                        results[self.RUNNING_CONFIG_CMD] = ssh.run_command(self.RUNNING_CONFIG_CMD)
            except Exception as exc:
                runtime.reachable_ssh = False
                runtime.save(update_fields=["reachable_ssh", "last_check"])
                if include_config:
                    self._record_config(device, success=False, error_message=str(exc))
                return {"device": device, "success": False, "error": str(exc)}

            runtime.reachable_ssh = True
            runtime.save(update_fields=["reachable_ssh", "last_check"])

            self._apply_version(device, runtime, results[self.VERSION_CMD])
            self._apply_inventory(device, results[self.INVENTORY_CMD])
            self._apply_interfaces(device, results[self.IF_STATUS_CMD], results[self.IF_IP_BRIEF_CMD])
            if include_config:
                config_result = results.get(self.RUNNING_CONFIG_CMD, {})
                self._record_config(
                    device,
                    success=not config_result.get("error"),
                    error_message=config_result.get("error"),
                    config_text=config_result.get("raw", "") if not config_result.get("error") else "",
                )

            return {"device": device, "success": True}

    # -------------------------------------------------
    # Parsers / appliers
    # -------------------------------------------------
    def _apply_version(self, device: Device, runtime: DeviceRuntimeStatus, result: dict):
        parsed = result.get("parsed")
        raw = result.get("raw", "") or ""

        serial = image = None
        uptime_seconds = None

        if parsed and isinstance(parsed, (list, tuple)) and parsed:
            entry = parsed[0]
            serial = (
                (entry.get("serial") or entry.get("serial_number") or "")
                if isinstance(entry, dict)
                else ""
            )
            if isinstance(serial, list):
                serial = serial[0] if serial else ""
            image = entry.get("version") or entry.get("running_image")
            uptime_seconds = self._parse_uptime(entry.get("uptime"))
        else:
            serial = self._parse_serial_from_text(raw)
            uptime_seconds = self._parse_uptime(self._extract_uptime_line(raw))
            image_match = self._parse_image_from_text(raw)
            image = image_match if image_match else None

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
            update_fields.extend(["uptime", "last_reboot"])
            runtime.uptime = timedelta(seconds=uptime_seconds)
            runtime.save(update_fields=["reachable_ssh", "last_check", "uptime"])
        else:
            runtime.save(update_fields=["reachable_ssh", "last_check"])

        device.save(update_fields=update_fields)

    def _apply_inventory(self, device: Device, result: dict):
        parsed = result.get("parsed") if isinstance(result, dict) else None
        if not parsed or not isinstance(parsed, (list, tuple)):
            return

        for entry in parsed:
            name = (entry.get("name") or entry.get("descr") or "Module").strip()
            description = entry.get("descr") or ""
            serial = entry.get("sn") or entry.get("serial") or ""
            if not serial or serial.upper() in ("N/A", "UNKNOWN", "N"):
                serial = f"UNKNOWN:{device.id}:{name}"

            DeviceModule.objects.update_or_create(
                device=device,
                name=name,
                serial_number=serial,
                defaults={"description": description or "", "vendor": None},
            )

    def _apply_interfaces(self, device: Device, status_result: dict, ip_result: dict):
        ip_map = {}
        parsed_ip = ip_result.get("parsed") if isinstance(ip_result, dict) else None
        if parsed_ip and isinstance(parsed_ip, (list, tuple)):
            for entry in parsed_ip:
                iface = entry.get("intf") or entry.get("interface")
                ipaddr = entry.get("ipaddr") or entry.get("ip_address")
                if iface and ipaddr and ipaddr.lower() != "unassigned":
                    ip_map[iface.strip()] = ipaddr.strip()

        parsed_status = status_result.get("parsed") if isinstance(status_result, dict) else None
        if not parsed_status or not isinstance(parsed_status, (list, tuple)):
            return

        for entry in parsed_status:
            name = (entry.get("port") or entry.get("interface") or "").strip()
            if not name:
                continue

            alias = (entry.get("name") or "").strip()
            vlan_value = (entry.get("vlan") or "").strip().lower()
            status_raw = (entry.get("status") or "").strip().lower()
            speed_raw = entry.get("speed") or ""
            speed = self._parse_speed(speed_raw)
            is_trunk = vlan_value == "trunk"

            interface_defaults = {
                "description": alias or "",
                "status": self._map_status(status_raw),
                "speed": speed,
                "is_trunk": is_trunk,
            }

            iface, _ = Interface.objects.update_or_create(
                device=device,
                name=name,
                defaults=interface_defaults,
            )

            if not is_trunk and vlan_value.isdigit():
                vlan_obj = VLAN.objects.filter(site=device.site, vlan_id=int(vlan_value)).first()
                iface.access_vlan = vlan_obj
            if name in ip_map:
                iface.ip_address = ip_map[name]
            iface.save()

    def _record_config(self, device: Device, *, success: bool, error_message: str | None = None, config_text: str = ""):
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

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------
    @staticmethod
    def _parse_speed(speed_raw):
        if not speed_raw:
            return None
        try:
            return int(re.sub(r"[^\d]", "", str(speed_raw)))
        except ValueError:
            return None

    @staticmethod
    def _map_status(status_raw: str):
        if not status_raw:
            return InterfaceStatusChoices.DOWN
        if "up" in status_raw and "down" not in status_raw:
            return InterfaceStatusChoices.UP
        if "notconnect" in status_raw:
            return InterfaceStatusChoices.NOTCONNECTED
        if "err" in status_raw:
            return InterfaceStatusChoices.ERR_DISABLED
        if "disabled" in status_raw:
            return InterfaceStatusChoices.DISABLED
        if "connected" in status_raw:
            return InterfaceStatusChoices.CONNECTED
        return InterfaceStatusChoices.DOWN

    @staticmethod
    def _parse_serial_from_text(raw: str):
        match = re.search(r"[Ss]erial [Nn]umber\s*[:#]?\s*([A-Z0-9\-]+)", raw or "")
        return match.group(1) if match else ""

    @staticmethod
    def _parse_uptime(uptime_str):
        if not uptime_str or not isinstance(uptime_str, str):
            return None
        total_seconds = 0
        patterns = {
            "year": r"(\d+)\s+year",
            "week": r"(\d+)\s+week",
            "day": r"(\d+)\s+day",
            "hour": r"(\d+)\s+hour",
            "minute": r"(\d+)\s+minute",
            "second": r"(\d+)\s+second",
        }
        for unit, pattern in patterns.items():
            m = re.search(pattern, uptime_str, re.IGNORECASE)
            if not m:
                continue
            val = int(m.group(1))
            if unit == "year":
                total_seconds += val * 365 * 24 * 3600
            elif unit == "week":
                total_seconds += val * 7 * 24 * 3600
            elif unit == "day":
                total_seconds += val * 24 * 3600
            elif unit == "hour":
                total_seconds += val * 3600
            elif unit == "minute":
                total_seconds += val * 60
            elif unit == "second":
                total_seconds += val
        return total_seconds or None

    @staticmethod
    def _extract_uptime_line(raw: str):
        for line in (raw or "").splitlines():
            if "uptime is" in line.lower():
                return line
        return ""
    
    @staticmethod
    def _parse_image_from_text(raw: str):
        match = re.search(r"\bVersion\s+([0-9]+(?:\.[0-9]+)*(?:\([^)]+\))?[A-Za-z0-9.]*)", raw, re.MULTILINE)
        return match.group(1) if match else None
