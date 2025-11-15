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
    area_name = serializers.CharField(source="area.name", read_only=True)

    class Meta:
        model = Rack
        fields = ["id", "name", "area", "area_name", "height", "description"]


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
    rack_name = serializers.CharField(source="rack.name", read_only=True)

    rack = serializers.PrimaryKeyRelatedField(queryset=Rack.objects.none())

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
            "site",
            "area",
            "area_name",
            "rack",
            "rack_name",
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
            "updated_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request", None)
        area_id = None

        # 1 — From POST/PUT/PATCH request body
        if request and hasattr(request, "data"):
            raw = request.data.get("area")
            if isinstance(raw, (int, str)):
                area_id = raw

        # 2 — From query params (GET /api/devices/?area=5)
        if not area_id and request:
            area_id = request.query_params.get("area")

        # 3 — From initial data (Browsable API form)
        if not area_id and isinstance(self.initial, dict):   # <-- Fix for initial=None
            area_id = self.initial.get("area")

        # 4 — From instance being edited
        if not area_id and self.instance:
            area_id = getattr(self.instance, "area_id", None)

        # 5 — Apply queryset
        if area_id:
            try:
                self.fields["rack"].queryset = Rack.objects.filter(area_id=area_id)
            except Exception:
                self.fields["rack"].queryset = Rack.objects.none()
        else:
            # Browsable API list view and GET list view MUST allow full queryset
            if self.parent and getattr(self.parent, "many", False):
                self.fields["rack"].queryset = Rack.objects.all()
            else:
                self.fields["rack"].queryset = Rack.objects.none()


    def validate(self, data):
        area = data.get("area") or getattr(self.instance, "area", None)
        rack = data.get("rack") or getattr(self.instance, "rack", None)

        if area and rack and rack.area_id != area.id:
            raise serializers.ValidationError({
                "rack": f"Rack '{rack.name}' does not belong to area '{area.name}'."
            })

        return data