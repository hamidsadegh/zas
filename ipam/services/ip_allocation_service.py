import ipaddress

from ipam.models import IPAddress, Prefix
from ipam.choices import IPAddressStatusChoices


class IPAllocationService:
    @staticmethod
    def next_available_ip(prefix: Prefix) -> str:
        network = ipaddress.ip_network(prefix.cidr, strict=True)

        used = {
            ipaddress.ip_address(ip.address)
            for ip in IPAddress.objects.filter(
                prefix=prefix
            ).exclude(status=IPAddressStatusChoices.DEPRECATED)
        }

        for ip in network.hosts():
            if ip not in used:
                return str(ip)

        raise RuntimeError(f"No available IPs in {prefix.cidr}")
