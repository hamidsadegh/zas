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
from dcim.choices import (
    InterfaceStatusChoices,
    InterfaceKindChoices,
    InterfaceModeChoices,
)
from network.adapters.netmiko import NetmikoAdapter
from network.choices import CliCommandsChoices as cli


class SyncService:

    def __init__(self, *, site):
        self.site = site
        self.now = timezone.now()
        self.VERSION_CMD = cli.VERSION_CMD
        self.INVENTORY_CMD = cli.INVENTORY_CMD
        self.IF_STATUS_CMD = cli.IF_STATUS_CMD
        self.IF_DESC_CMD = cli.IF_DESC_CMD
        self.IF_IP_BRIEF_CMD = cli.IF_IP_BRIEF_CMD
        self.PORTCHANNEL_SUMMARY_CMD = cli.PORTCHANNEL_SUMMARY_ISO_CMD
        self.RUNNING_CONFIG_CMD = cli.RUNNING_CONFIG_CMD

    # =================================================
    # PUBLIC API
    # =================================================
    def sync_device(self, device: Device, *, include_config: bool = True) -> dict:
        with transaction.atomic():
            runtime, _ = DeviceRuntimeStatus.objects.get_or_create(device=device)
            runtime.last_check = self.now

            if device.device_type == 'cisco_nxos':  # NX-OS requires special handling
                self.PORTCHANNEL_SUMMARY_CMD = cli.PORTCHANNEL_SUMMARY_NXOS_CMD
            else:
                self.PORTCHANNEL_SUMMARY_CMD = cli.PORTCHANNEL_SUMMARY_ISO_CMD

            # SSH Connection and Data Retrieval
            try:
                with NetmikoAdapter(device) as ssh:
                    results = {
                        self.VERSION_CMD: ssh.run_command(self.VERSION_CMD),
                        self.INVENTORY_CMD: ssh.run_command(self.INVENTORY_CMD),
                        self.IF_STATUS_CMD: ssh.run_command(self.IF_STATUS_CMD),
                        self.IF_DESC_CMD: ssh.run_command(self.IF_DESC_CMD),
                        self.IF_IP_BRIEF_CMD: ssh.run_command(self.IF_IP_BRIEF_CMD),
                        self.PORTCHANNEL_SUMMARY_CMD: ssh.run_command(self.PORTCHANNEL_SUMMARY_CMD),
                    }
                    if include_config:
                        results[self.RUNNING_CONFIG_CMD] = ssh.run_command(self.RUNNING_CONFIG_CMD)

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

            self._apply_interfaces(
                device=device,
                status_result=results[self.IF_STATUS_CMD],
                desc_result=results[self.IF_DESC_CMD],
                ip_result=results[self.IF_IP_BRIEF_CMD],
                po_result=results[self.PORTCHANNEL_SUMMARY_CMD],
            )

            if include_config:
                cfg = results.get(self.RUNNING_CONFIG_CMD, {})
                self._record_config(
                    device=device,
                    success=not cfg.get("error"),
                    error_message=cfg.get("error"),
                    config_text=cfg.get("raw", "") if not cfg.get("error") else "",
                )

            return {"device": device, "success": True}

    # =================================================
    # VERSION / INVENTORY / CONFIG
    # =================================================
    def _apply_version(self, device: Device, runtime: DeviceRuntimeStatus, result: dict):
        parsed = result.get("parsed")
        raw = result.get("raw", "") or ""

        serial = image = None
        uptime_seconds = None

        if parsed and isinstance(parsed, list):
            entry = parsed[0]
            serial = entry.get("serial") or entry.get("serial_number")
            if isinstance(serial, list): 
                serial = serial[0] if serial else ""
            image = entry.get("version") or entry.get("running_image") or entry.get("os")
            uptime_seconds = self._parse_uptime(entry.get("uptime"))
        else:
            serial = self._parse_serial_from_text(raw)
            uptime_seconds = self._parse_uptime(self._extract_uptime_line(raw))
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

        for entry in parsed:
            name = (entry.get("name") or entry.get("descr") or "Module").strip()
            serial = entry.get("sn") or entry.get("serial") or ""
            descr = entry.get("descr") or ""

            if not serial or serial.upper() in {"N/A", "UNKNOWN"}:
                serial = f"UNKNOWN:{device.id}:{name}"

            DeviceModule.objects.update_or_create(
                device=device,
                name=name,
                serial_number=serial,
                defaults={
                    "description": descr,
                    "vendor": None,
                },
            )

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
        lag_map = {}

        # ---- descriptions ----
        for e in desc_result.get("parsed", []) or []:
            name = self._normalize_iface(e.get("port") or e.get("interface"))
            if "Vl" in name:
                continue  # Skip VLAN interfaces here; handled via ip brief
            desc_map[name] = (e.get("description") or "").strip()

        # ---- status ----
        for e in status_result.get("parsed", []) or []:
            name = self._normalize_iface(e.get("port") or e.get("interface"))
            status_map[name] = {
                "status": (e.get("status") or "").lower(),
                "vlan": (e.get("vlan") or "").lower(),
                "speed": self._parse_speed(e.get("speed")),
            }

        # ---- ip brief ----
        for e in ip_result.get("parsed", []) or []:
            name = self._normalize_iface(e.get("intf") or e.get("interface"))
            ip = e.get("ipaddr") or e.get("ip_address")
            if ip and ip.lower() != "unassigned":
                ip_map[name] = ip.strip()

        # ---- port-channel ----
        for e in po_result.get("parsed", []) or []:
            po = self._normalize_iface(e.get("port_channel"))
            for m in (e.get("interfaces") or "").split():
                lag_map[self._normalize_iface(m)] = po

        # ---- create all interfaces ----
        all_names = set(status_map) | set(desc_map) | set(ip_map) | set(lag_map.values())
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

        # ---- operational attributes ----
        for name, iface in iface_objs.items():
            data = status_map.get(name)
            if not data:
                continue
            print(name, data)
            iface.status = self._map_status(data["status"])
            iface.speed = data["speed"]
            iface.description = desc_map.get(name, "")
            iface.is_trunk = "trunk" in (data.get("vlan") or "")
            iface.save()

        # ---- TEMP: IP on interface (pre-IPAM) ----
        for name, ip in ip_map.items():
            iface = iface_objs.get(name)
            if iface:
                iface.ip_address = ip
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
        return InterfaceStatusChoices.DOWN

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
    def _extract_uptime_line(raw: str):
        for line in (raw or "").splitlines():
            if "uptime is" in line.lower():
                return line
        return ""

    @staticmethod
    def _parse_image_from_text(raw: str):
        m = re.search(r"\bVersion\s+([0-9A-Za-z().-]+)", raw or "")
        return m.group(1) if m else None
