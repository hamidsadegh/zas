# automation/engine/ssh_engine.py

from typing import Any, Dict, Iterable
from netmiko import ConnectHandler

from dcim.models import Device
from accounts.models import SiteCredential
from automation.choices import NETMIKO_PLATFORM_MAP, DevicePlatformChoices

class SSHEngine:
    """
    Per-device SSH engine using Netmiko.

    Usage:
        ssh = SSHEngine(device)
        out = ssh.run_command("show version")
    """

    def __init__(self, device: Device):
        self.device = device

        # Fetch site credentials
        try:
            credential = SiteCredential.objects.select_related("site").get(site=device.site)
        except SiteCredential.DoesNotExist as exc:
            raise SiteCredential.DoesNotExist(
                f"No credentials configured for site '{device.site.name}'."
            ) from exc
        self.conn_params: Dict[str, Any] = {
            "device_type": self._netmiko_platform(),
            "host": getattr(device, "management_ip", None),
            "username": credential.ssh_username,
            "password": credential.ssh_password,
            "port": credential.ssh_port,
            "timeout": 30,
        }

    def _netmiko_platform(self) -> str:
        """
        Map ZAS device attributes to a Netmiko platform string.
        Returns:
            Netmiko platform string.
        """
        # try to use platform slug if available
        platform = getattr(self.device, "platform", DevicePlatformChoices.UNKNOWN)
        return NETMIKO_PLATFORM_MAP.get(platform, "autodetect")

    def run_command(self, command: str, timeout: int = 30) -> str:
        """
        Run a single show command and return its output.
        """
        with ConnectHandler(**self.conn_params) as conn:
            output = conn.send_command(command)
            return output

    def send_config(self, commands: Iterable[str]) -> str:
        """
        Send configuration commands and return the output.
        """
        with ConnectHandler(**self.conn_params) as conn:
            output = conn.send_config_set(list(commands))
            return output
