from ipaddress import ip_network, ip_address
from rest_framework import serializers
from ipam.models import VRF, Prefix, IPAddress

class VRFSerializer(serializers.ModelSerializer):
    class Meta:
        model = VRF
        fields = ["id", "name", "rd", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

class PrefixSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prefix
        fields = [
            "id", "vrf", "prefix", "status", "role", "description",
            "is_pool", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_prefix(self, value):
        # Ensure canonical CIDR formatting (Postgres inet/cidr also helps, but keep API strict)
        try:
            net = ip_network(str(value), strict=True)
        except ValueError as e:
            raise serializers.ValidationError(str(e))
        return str(net)

    def validate(self, attrs):
        # Overlap protection (v1: block overlap within same VRF)
        vrf = attrs.get("vrf") or getattr(self.instance, "vrf", None)
        prefix = attrs.get("prefix") or getattr(self.instance, "prefix", None)

        if vrf and prefix:
            net = ip_network(str(prefix), strict=True)
            qs = Prefix.objects.filter(vrf=vrf)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            for other in qs.only("id", "prefix"):
                other_net = ip_network(str(other.prefix), strict=True)
                if net.overlaps(other_net):
                    raise serializers.ValidationError({
                        "prefix": f"Overlaps with existing prefix {other.prefix} (id={other.id})."
                    })
        return attrs

class IPAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = IPAddress
        fields = [
            "id", "vrf", "address", "status", "dns_name", "description",
            "assigned_object_type", "assigned_object_id",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_address(self, value):
        # Accept "10.0.0.1" and normalize to host prefix, or require CIDR if you prefer
        s = str(value).strip()
        if "/" not in s:
            # assume host
            ip = ip_address(s)
            s = f"{ip}/32" if ip.version == 4 else f"{ip}/128"

        try:
            net = ip_network(s, strict=False)  # strict=False allows host/len
        except ValueError as e:
            raise serializers.ValidationError(str(e))

        # Enforce host address only
        if (net.num_addresses != 1):
            raise serializers.ValidationError("IP address must be a host (/32 or /128).")

        return str(net)
