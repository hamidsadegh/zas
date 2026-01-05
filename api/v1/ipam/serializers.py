import ipaddress
from rest_framework import serializers
from ipam.models import VRF, Prefix, IPAddress


class VRFSerializer(serializers.ModelSerializer):
    prefix_count = serializers.IntegerField(source="prefixes.count", read_only=True)

    class Meta:
        model = VRF
        fields = ["id", "name", "site", "rd", "description", "created_at", "prefix_count"]
        read_only_fields = ["id", "created_at", "prefix_count"]


class PrefixSerializer(serializers.ModelSerializer):
    ip_count = serializers.IntegerField(source="ip_addresses.count", read_only=True)

    class Meta:
        model = Prefix
        fields = [
            "id",
            "cidr",
            "site",
            "vrf",
            "vlan",
            "parent",
            "status",
            "role",
            "description",
            "created_at",
            "ip_count",
        ]
        read_only_fields = ["id", "created_at", "ip_count"]

    def validate_cidr(self, value):
        try:
            net = ipaddress.ip_network(value, strict=True)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))
        return str(net)


class IPAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = IPAddress
        fields = ["id", "address", "prefix", "interface", "status", "role", "hostname", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        prefix = attrs.get("prefix") or getattr(self.instance, "prefix", None)
        address = attrs.get("address") or getattr(self.instance, "address", None)
        interface = attrs.get("interface") or getattr(self.instance, "interface", None)
        if not prefix or not address:
            return attrs

        try:
            ip_obj = ipaddress.ip_address(address)
        except ValueError:
            raise serializers.ValidationError({"address": "Enter a valid IP address."})

        network = ipaddress.ip_network(prefix.cidr, strict=False)
        if ip_obj not in network:
            raise serializers.ValidationError({"address": "IP must belong to the selected prefix."})

        vrf_id = prefix.vrf_id
        qs = IPAddress.objects.filter(address=address, prefix__vrf_id=vrf_id)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError({"address": "IP address already exists in this VRF."})

        return attrs
