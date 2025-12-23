import ipaddress

from django.core.exceptions import ValidationError

from ipam.models import IPAddress
from ipam.choices import IPAddressRoleChoices, IPAddressStatusChoices


class IPAddressValidationService:
    """Validation logic for IP address rules."""

    def __init__(self, ip_address: IPAddress):
        self.ip_address = ip_address

    def validate(self) -> None:
        errors = {}

        if not self.ip_address.prefix_id and not self.ip_address.prefix:
            errors["prefix"] = "IP address must belong to a prefix."

        ip_obj = self._parse_ip(self.ip_address.address, errors)
        prefix_network = self._parse_prefix_network(errors)

        if errors:
            raise ValidationError(errors)

        if prefix_network and ip_obj not in prefix_network:
            errors["address"] = "IP address must be inside the assigned prefix."

        if self.ip_address.interface:
            self._validate_interface_site(errors)
            if self.ip_address.role == IPAddressRoleChoices.PRIMARY:
                self._validate_primary_role(ip_obj, errors)

        if errors:
            raise ValidationError(errors)

    def _parse_ip(self, value: str, errors: dict) -> ipaddress._BaseAddress:
        try:
            return ipaddress.ip_address(value)
        except ValueError as exc:
            errors["address"] = f"Invalid IP address: {exc}"
            return None

    def _parse_prefix_network(self, errors: dict) -> ipaddress._BaseNetwork | None:
        prefix = self.ip_address.prefix
        if not prefix:
            return None

        try:
            return ipaddress.ip_network(prefix.cidr, strict=True)
        except ValueError as exc:
            errors["prefix"] = f"Invalid prefix on assignment: {exc}"
            return None

    def _validate_interface_site(self, errors: dict) -> None:
        interface = self.ip_address.interface
        prefix = self.ip_address.prefix

        if not interface or not prefix:
            return

        device_site_id = getattr(interface.device, "site_id", None)
        if device_site_id != prefix.site_id:
            errors["interface"] = "Interface device site must match prefix site."

    def _validate_primary_role(
        self, ip_obj: ipaddress._BaseAddress, errors: dict
    ) -> None:
        if not self.ip_address.interface or ip_obj is None:
            return

        primary_qs = (
            IPAddress.objects.filter(
                interface_id=self.ip_address.interface_id,
                role=IPAddressRoleChoices.PRIMARY,
            )
            .exclude(pk=self.ip_address.pk)
            .exclude(status=IPAddressStatusChoices.DEPRECATED)
        )

        for existing in primary_qs:
            try:
                existing_ip = ipaddress.ip_address(existing.address)
            except ValueError:
                continue

            if existing_ip.version == ip_obj.version:
                errors["role"] = (
                    f"Interface {self.ip_address.interface} already has a primary "
                    f"IPv{ip_obj.version} address."
                )
                return
