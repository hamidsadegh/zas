# automation/engine/ssh_engine.py

from typing import Any, Dict, Iterable, List, Optional

from netmiko import ConnectHandler

from dcim.models import Device
from accounts.models import SiteCredential


class SSHEngine:
    """
    Per-device SSH engine using Netmiko.

    Usage:
        ssh = SSHEngine(device)
        out = ssh.run_command("show version")
    """

    def __init__(self, device: Device):
        self.device = device
        self.conn_params: Dict[str, Any] = {
            "device_type": self._netmiko_platform(),
            "host": getattr(device, "management_ip", None),
            "username": SiteCredential.objects.get(site=device.site).ssh_username,
            "password": SiteCredential.objects.get(site=device.site).ssh_password,
            "port": SiteCredential.objects.get(site=device.site).ssh_port,
            "timeout": 10,
        }

    def _netmiko_platform(self) -> str:
        """
        Map ZAS device attributes to a Netmiko platform string.

        Adjust this mapping to fit your actual Device/Platform model.
        """
        # try to use platform slug if available
        platform_slug = None
        platform = getattr(self.device, "platform", None)
        if platform is not None:
            platform_slug = getattr(platform, "slug", None) or getattr(platform, "name", None)

        # fallback: use device_type as string (e.g. "catalyst", "nexus", etc.)
        device_type_str = getattr(self.device, "device_type", None)
        if hasattr(device_type_str, "slug"):
            device_type_str = device_type_str.slug
        elif hasattr(device_type_str, "model"):
            device_type_str = device_type_str.model

        device_type_str = (device_type_str or "").lower()
        platform_slug = (platform_slug or "").lower()

        # simple mapping
        mapping = {
            "catalyst": "cisco_ios",
            "router": "cisco_ios",
            "nexus": "cisco_nxos",
            "asa": "cisco_asa",
            "firewall": "cisco_asa",
        }

        # decide based on platform or device_type string
        for key, netmiko_type in mapping.items():
            if key in platform_slug or key in device_type_str:
                return netmiko_type

        # last resort
        return "autodetect"

    def run_command(self, command: str, timeout: int = 30) -> str:
        """
        Run a single show command and return its output.
        """
        with ConnectHandler(**self.conn_params) as conn:
            output = conn.send_command(command, timeout=timeout)
            return output

    def send_config(self, commands: Iterable[str]) -> str:
        """
        Send configuration commands and return the output.
        """
        with ConnectHandler(**self.conn_params) as conn:
            output = conn.send_config_set(list(commands))
            return output
