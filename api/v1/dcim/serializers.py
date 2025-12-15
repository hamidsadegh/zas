from rest_framework import serializers  # type: ignore
from dcim.models import (
    Area,
    Device,
    DeviceConfiguration,
    DeviceModule,
    DeviceRole,
    DeviceType,
    Interface,
    Organization,
    Rack,
    Site,
    VLAN,
    Vendor,
)


# -----------------------
# Organization Serializer
# -----------------------
class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "description", "created_at", "updated_at"]


# -----------------------
# Site Serializer
# -----------------------
class SiteSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = Site
        fields = [
            "id",
            "name",
            "description",
            "organization",
            "organization_name",
            "created_at",
            "updated_at",
        ]


# -----------------------
# Area Serializer
# -----------------------
class AreaSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)
    site_name = serializers.CharField(source="site.name", read_only=True)
    organization = serializers.PrimaryKeyRelatedField(source="site.organization", read_only=True)

    class Meta:
        model = Area
        fields = [
            "id",
            "name",
            "parent",
            "parent_name",
            "description",
            "site",
            "site_name",
            "organization",
        ]

    def validate(self, attrs):
        site = attrs.get("site") or getattr(self.instance, "site", None)
        parent = attrs.get("parent") or getattr(self.instance, "parent", None)
        if parent and site and parent.site_id != site.id:
            raise serializers.ValidationError({
                "parent": "Parent area must belong to the same site as this area."
            })
        return attrs


# -----------------------
# Rack Serializer
# -----------------------
class RackSerializer(serializers.ModelSerializer):
    area_name = serializers.CharField(source="area.name", read_only=True)
    site = serializers.PrimaryKeyRelatedField(source="area.site", read_only=True)
    site_name = serializers.CharField(source="area.site.name", read_only=True)

    class Meta:
        model = Rack
        fields = ["id", "name", "area", "area_name", "site", "site_name", "description"]


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
        fields = [
            "id",
            "vendor",
            "vendor_name",
            "model",
            "platform",
            "description",
        ]


# -----------------------
# DeviceModule Serializer
# -----------------------
class DeviceModuleSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    device_name = serializers.CharField(source="device.name", read_only=True)

    class Meta:
        model = DeviceModule
        fields = ["id", "name", "description", "vendor", "vendor_name", "device", "device_name", "serial_number"]


# -----------------------
# DeviceConfiguration Serializer
# -----------------------
class DeviceConfigurationSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)
    size = serializers.SerializerMethodField()

    class Meta:
        model = DeviceConfiguration
        fields = [
            "id",
            "device",
            "device_name",
            "backup_time",
            "success",
            "error_message",
            "config_text",
            "size",
        ]
        read_only_fields = fields

    def get_size(self, obj):
        return len(obj.config_text or "")


# -----------------------
# Interface Serializer
# -----------------------
class InterfaceSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)

    class Meta:
        model = Interface
        fields = [
            "id",
            "name",
            "device",
            "device_name",
            "description",
            "mac_address",
            "ip_address",
            "status",
            "endpoint",
            "speed",
            "access_vlan",
            "trunk_vlans",
            "is_trunk",
        ]


# -----------------------
# Device Serializer
# -----------------------
class DeviceSerializer(serializers.ModelSerializer):
    # Read-only convenience fields
    area_name = serializers.CharField(source="area.name", read_only=True)
    device_type_name = serializers.CharField(source="device_type.model", read_only=True)
    device_type_vendor_name = serializers.CharField(source="device_type.vendor.name",read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    rack_name = serializers.CharField(source="rack.name", read_only=True)
    site_name = serializers.CharField(source="site.name", read_only=True)
    organization = serializers.PrimaryKeyRelatedField(source="site.organization", read_only=True)
    organization_name = serializers.CharField(source="site.organization.name", read_only=True)
    modules = DeviceModuleSerializer(many=True, read_only=True)
    reachable_ping = serializers.SerializerMethodField()
    reachable_snmp = serializers.SerializerMethodField()
    reachable_ssh = serializers.SerializerMethodField()
    reachable_netconf = serializers.SerializerMethodField()
    uptime = serializers.SerializerMethodField()


    # Writable relationship fields
    area = serializers.PrimaryKeyRelatedField(queryset=Area.objects.all(), required=True, help_text="Area where the device is located.")
    rack = serializers.PrimaryKeyRelatedField(queryset=Rack.objects.none(), required=False, allow_null=True,
                                              help_text="Rack where the device is mounted (optional).")

    class Meta:
        model = Device
        fields = [
            "id",
            "name",
            "management_ip",
            "mac_address",
            "serial_number",
            "inventory_number",
            "site",
            "site_name",
            "organization",
            "organization_name",
            "area",
            "area_name",
            "rack",
            "rack_name",
            "device_type",
            "device_type_name",
            "device_type_vendor_name",
            "role",
            "role_name",
            "image_version",
            "status",
            "reachable_ping",
            "reachable_snmp",
            "reachable_ssh",
            "reachable_netconf",
            "uptime",
            "created_at",
            "updated_at",
            "modules",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request", None)
        area_id = self._resolve_value("area", request)
        site_id = self._resolve_value("site", request)

        area_field = self.fields.get("area")
        rack_field = self.fields.get("rack")

        # Restrict area queryset to the selected site
        if site_id:
            try:
                area_field.queryset = Area.objects.filter(site_id=site_id)
            except Exception:
                area_field.queryset = Area.objects.none()
        else:
            area_field.queryset = Area.objects.none()

        # Restrict rack queryset to the selected area
        if area_id:
            try:
                rack_field.queryset = Rack.objects.filter(area_id=area_id)
            except Exception:
                rack_field.queryset = Rack.objects.none()
        else:
            rack_field.queryset = Rack.objects.none()

    def _resolve_value(self, field_name, request):
        """
        Determine the current value for a related field across request data, initial data and instance.
        """
        value = None
        if request and hasattr(request, "data"):
            raw = request.data.get(field_name)
            if isinstance(raw, (int, str)):
                value = raw

        if not value and request:
            candidate = request.query_params.get(field_name)
            if candidate:
                value = candidate

        if not value and hasattr(self, "initial_data") and isinstance(self.initial_data, dict):
            initial_value = self.initial_data.get(field_name)
            if initial_value:
                value = initial_value

        if not value and self.instance:
            value = getattr(self.instance, f"{field_name}_id", None)

        return value

    def validate(self, data):
        site = data.get("site") or getattr(self.instance, "site", None)
        area = data.get("area") or getattr(self.instance, "area", None)
        rack = data.get("rack") or getattr(self.instance, "rack", None)

        if site is None:
            raise serializers.ValidationError({"site": "A site must be specified for each device."})

        if area and area.site_id != site.id:
            raise serializers.ValidationError({
                "area": f"Area '{area.name}' does not belong to site '{site.name}'."
            })

        if area and rack and rack.area_id != area.id:
            raise serializers.ValidationError({
                "rack": f"Rack '{rack.name}' does not belong to area '{area.name}'."
            })

        if rack and not area and rack.area.site_id != site.id:
            raise serializers.ValidationError({
                "rack": f"Rack '{rack.name}' does not belong to site '{site.name}'."
            })

        return data

    def get_reachable_ping(self, obj):
        return getattr(getattr(obj, "runtime", None), "reachable_ping", False)

    def get_reachable_snmp(self, obj):
        return getattr(getattr(obj, "runtime", None), "reachable_snmp", False)

    def get_reachable_ssh(self, obj):
        return getattr(getattr(obj, "runtime", None), "reachable_ssh", False)

    def get_reachable_netconf(self, obj):
        return getattr(getattr(obj, "runtime", None), "reachable_netconf", False)

    def get_uptime(self, obj):
        return getattr(getattr(obj, "runtime", None), "uptime", None)
