import ipaddress
from typing import Iterable, Set

from django.core.exceptions import ValidationError

from ipam.models import Prefix


class PrefixValidationService:
    """Validation logic for Prefix domain rules."""

    def __init__(self, prefix: Prefix):
        self.prefix = prefix

    def validate(self) -> None:
        errors = {}

        if not self.prefix.site_id:
            errors["site"] = "Prefix must be assigned to a site."

        network = self._parse_network(self.prefix.cidr, errors, field="cidr")

        if errors:
            raise ValidationError(errors)

        if self.prefix.vrf and self.prefix.vrf.site_id != self.prefix.site_id:
            errors["vrf"] = "VRF site must match the prefix site."

        if self.prefix.parent:
            self._validate_parent_relationship(network, errors)

        if errors:
            raise ValidationError(errors)

        self._validate_overlaps(network, errors)

        if errors:
            raise ValidationError(errors)

    def _parse_network(self, value: str, errors: dict, field: str) -> ipaddress._BaseNetwork:
        try:
            return ipaddress.ip_network(value, strict=True)
        except ValueError as exc:
            errors[field] = f"Invalid network: {exc}"
            return None

    def _validate_parent_relationship(
        self, network: ipaddress._BaseNetwork, errors: dict
    ) -> ipaddress._BaseNetwork | None:
        parent = self.prefix.parent

        if network is None:
            return None

        if parent.pk is None:
            errors["parent"] = "Parent prefix must be saved before assignment."
            return None

        if parent.site_id != self.prefix.site_id:
            errors["parent"] = "Parent prefix must belong to the same site."
            return None

        if parent.vrf_id != self.prefix.vrf_id:
            errors["parent"] = "Parent prefix must belong to the same VRF."
            return None

        parent_network = self._parse_network(parent.cidr, errors, field="parent")
        if errors:
            return parent_network

        if not network.subnet_of(parent_network):
            errors["cidr"] = "Prefix must be contained within its parent."
            return parent_network

        if network == parent_network:
            errors["cidr"] = "Prefix must be more specific than its parent."

        return parent_network

    def _validate_overlaps(
        self, network: ipaddress._BaseNetwork, errors: dict
    ) -> None:
        """Prevent overlaps in the same site/VRF unless hierarchical."""
        if network is None:
            return

        qs = Prefix.objects.filter(site_id=self.prefix.site_id, vrf=self.prefix.vrf).exclude(
            pk=self.prefix.pk
        )

        containing_prefixes = []

        for other in qs:
            try:
                other_network = ipaddress.ip_network(other.cidr, strict=True)
            except ValueError:
                # Skip malformed stored data; allow dedicated cleanup later.
                continue

            if network.overlaps(other_network):
                if network == other_network:
                    errors["cidr"] = (
                        f"Prefix {self.prefix.cidr} already exists for this site/VRF."
                    )
                    return

                if network.subnet_of(other_network):
                    containing_prefixes.append(other)
                    continue

                if not other_network.subnet_of(network):
                    errors["cidr"] = (
                        f"Prefix {self.prefix.cidr} overlaps with {other.cidr} in the same site/VRF."
                    )
                    return

        if containing_prefixes and not self._has_ancestor(containing_prefixes):
            names = ", ".join(prefix.cidr for prefix in containing_prefixes[:3])
            suffix = "..." if len(containing_prefixes) > 3 else ""
            errors["parent"] = (
                f"Prefix {self.prefix.cidr} is covered by existing prefixes ({names}{suffix}). "
                "Assign the most specific containing prefix as parent."
            )

    def _has_ancestor(self, candidates: Iterable[Prefix]) -> bool:
        candidate_ids: Set[str] = {p.pk for p in candidates if p.pk}
        parent = self.prefix.parent

        while parent:
            if parent.pk in candidate_ids:
                return True
            parent = parent.parent
        return False
