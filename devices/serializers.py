from rest_framework import serializers
from .models import (
    Device,
    Area,
    Rack,
    DeviceRole,
    Vendor,
    DeviceType,
    Interface,
    DeviceConfiguration,
    ModuleType,
    Organization,
)


# -----------------------
# Organization Serializer
# -----------------------
class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "description", "created_at", "updated_at"]


# -----------------------
# Area Serializer
# -----------------------
class AreaSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = Area
        fields = ["id", "name", "parent", "parent_name", "description", "organization", "organization_name"]


# -----------------------
# Rack Serializer
# -----------------------
class RackSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source="site.name", read_only=True)

    class Meta:
        model = Rack
        fields = ["id", "name", "site", "site_name", "height", "description"]


# -----------------------
# DeviceRole Serializer
# -----------------------
class DeviceRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceRole
        fields = ["id", "name", "description", "created_at"]


# -----------------------
# Vendor Serializer
# -----------------------
class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ["id", "name", "website", "created_at"]


# -----------------------
# DeviceType Serializer
# -----------------------
class DeviceTypeSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)

    class Meta:
        model = DeviceType
        fields = ["id", "vendor", "vendor_name", "model", "category", "description"]


# -----------------------
# ModuleType Serializer
# -----------------------
class ModuleTypeSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)

    class Meta:
        model = ModuleType
        fields = ["id", "name", "vendor", "vendor_name", "description"]


# -----------------------
# DeviceConfiguration Serializer
# -----------------------
class DeviceConfigurationSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)

    class Meta:
        model = DeviceConfiguration
        fields = ["id", "device", "device_name", "config_text", "last_updated"]


# -----------------------
# Interface Serializer
# -----------------------
class InterfaceSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)

    class Meta:
        model = Interface
        fields = ["id", "name", "device", "device_name", "description", "mac_address", "ip_address", "status", "endpoint", "speed"]


# -----------------------
# Device Serializer
# -----------------------
class DeviceSerializer(serializers.ModelSerializer):
    area_name = serializers.CharField(source="area.name", read_only=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    device_type_name = serializers.CharField(source="device_type.model", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)

    class Meta:
        model = Device
        fields = [
            "id",
            "name",
            "management_ip",
            "mac_address",
            "serial_number",
            "inventory_number",
            "organization",
            "area",
            "area_name",
            "vendor",
            "vendor_name",
            "device_type",
            "device_type_name",
            "role",
            "role_name",
            "image_version",
            "status",
            "uptime",
            "created_at",
            "updated_at"
        ]
