from accounts.models import SSHCredential
from automation.choices import NETMIKO_PLATFORM_MAP
from automation.platform import resolve_platform


class ConnectionService:
    @staticmethod
    def build_ssh_params(device):
        credential = (
            SSHCredential.objects
            .select_related("site")
            .filter(site=device.site)
            .first()
        )

        if not credential:
            raise SSHCredential.DoesNotExist(
                f"No SSH credentials configured for site '{device.site.name}'."
            )

        platform = resolve_platform(device)
        username = credential.ssh_username
        if device.tags.filter(name__iexact="aci_fabric").exists():
            prefix = "apic#ISE\\\\"
            if not username.startswith(prefix):
                username = f"{prefix}{username}"

        return {
            "device_type": NETMIKO_PLATFORM_MAP.get(platform, "autodetect"),
            "host": device.management_ip,
            "username": username,
            "password": credential.ssh_password,
            "port": credential.ssh_port,
            "timeout": 30,
        }
