from django.contrib import admin
from django.http import HttpResponse
from django.urls import reverse
from io import BytesIO
from django import forms
import pandas as pd  # pyright: ignore[reportMissingModuleSource, reportMissingImports]
from django.utils.timezone import localtime
from .models import (
    Organization,
    Area,
    Rack,
    DeviceRole,
    Vendor,
    DeviceType,
    Device,
    DeviceConfiguration,
    Interface,
    DeviceModule,
)

# -----------------------
# Organization Admin
# -----------------------
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "created_at", "updated_at")
    search_fields = ("name",)


# -----------------------
# Area Admin (hierarchical)
# -----------------------
@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "organization")
    list_filter = ("organization",)
    search_fields = ("name",)
    ordering = ("organization", "parent", "name")


# -----------------------
# Rack Admin
# -----------------------
@admin.register(Rack)
class RackAdmin(admin.ModelAdmin):
    list_display = ("name", "area", "height", "description")
    list_filter = ("area",)
    search_fields = ("name",)


# -----------------------
# DeviceRole Admin
# -----------------------
@admin.register(DeviceRole)
class DeviceRoleAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "created_at")
    search_fields = ("name",)


# -----------------------
# Vendor Admin
# -----------------------
@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "website", "created_at")
    search_fields = ("name",)



# -----------------------
# DeviceType Admin
# -----------------------
@admin.register(DeviceType)
class DeviceTypeAdmin(admin.ModelAdmin):
    list_display = ("model", "vendor", "category")
    list_filter = ("vendor", "category")
    search_fields = ("model",)


# -----------------------
# DeviceModule Admin
# -----------------------
@admin.register(DeviceModule)
class DeviceModuleAdmin(admin.ModelAdmin):
    list_display = ("name", "device", "serial_number", "vendor", "description")
    list_filter = ("vendor", "device")
    search_fields = ("name",)


# -----------------------
# Inline DeviceConfiguration for DeviceAdmin
# -----------------------
class DeviceConfigurationInline(admin.StackedInline):
    model = DeviceConfiguration
    extra = 0
    readonly_fields = ("last_updated",)


class DeviceModuleInline(admin.TabularInline):
    model = DeviceModule
    extra = 1
    fields = ("name", "serial_number", "vendor", "description")
    autocomplete_fields = ("vendor",)


# ------------------------------
# Import Form
# ------------------------------
class ImportExcelForm(forms.Form):
    excel_file = forms.FileField(label="Select Excel file")


from django import forms
from django.urls import reverse
from .models import Device, Rack


class DeviceAdminForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 1. Add racks-URL to the Area field for JS dynamic loading
        self.fields["area"].widget.widget.attrs["data-racks-url"] = reverse("racks_for_area")

        # 2. Prepare the Rack queryset depending on current area
        rack_field = self.fields.get("rack")
        area_id = self._current_area_id()

        if area_id:
            rack_field.queryset = Rack.objects.filter(area_id=area_id)
        else:
            rack_field.queryset = Rack.objects.none()
            rack_field.help_text = "Racks will appear after selecting an Area."

        # 3. Pass current rack as attribute for JS pre-selection
        current_rack_id = self._current_rack_id()
        rack_field.widget.attrs["data-current-value"] = (
            str(current_rack_id) if current_rack_id else ""
        )

    # Helpers — determine selected area/rack from POST or instance
    def _current_area_id(self):
        """Resolve area from POST data or instance."""
        if self.data.get("area"):
            return self.data.get("area")

        if self.instance and self.instance.pk:
            return self.instance.area_id

        return None

    def _current_rack_id(self):
        """Resolve rack from POST data or instance."""
        if self.data.get("rack"):
            return self.data.get("rack")

        if self.instance and self.instance.pk:
            return self.instance.rack_id

        return None


# ------------------------------
# Admin Actions
# ------------------------------
@admin.action(description="Export selected devices to Excel")
def export_devices_to_excel(modeladmin, request, queryset):
    """
    Export selected devices to an Excel file.
    Works as a Django admin action.
    """
    # Prepare DataFrame including related fields
    data = []
    for device in queryset:
        data.append({
            "Name": device.name,
            "Management IP": device.management_ip,
            "MAC Address": device.mac_address,
            "Serial Number": device.serial_number,
            "Inventory Number": device.inventory_number,
            "Organization": device.organization.name if device.organization else "-",
            "Area": str(device.area) if device.area else "-",
            "Rack": device.rack.name if device.rack else "-",
            "Vendor": device.vendor.name if device.vendor else "-",
            "Device Type": device.device_type.model if device.device_type else "-",
            "Role": device.role.name if device.role else "-",
            "Status": device.status,
            "Image Version": device.image_version,
            "Site": device.site,
            "Created At": localtime(device.created_at).replace(tzinfo=None) if device.created_at else "-",
            "Updated At": localtime(device.updated_at).replace(tzinfo=None) if device.updated_at else "-",

        })

    df = pd.DataFrame(data)
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=devices_export.xlsx'
    return response
# ------------------------------
# Device Admin
# ------------------------------
@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    form = DeviceAdminForm
    list_display = (
        "name",
        "management_ip",
        "status",
        "site",
        "rack",
        "device_type",
        "serial_number",
        "organization",
        "area",
        "image_version",
    )
    search_fields = (
        "name",
        "management_ip",
        "serial_number",
        "inventory_number",
        "device_type__model",
        "vendor__name",
        "area__name",
        "organization__name",
        "site",
    )
    list_filter = (
        "status",
        "site",
        "device_type",
        "vendor",
        "organization",
        "area",
    )
    actions = [export_devices_to_excel]
    inlines = [DeviceModuleInline, DeviceConfigurationInline]

    class Media:
        js = ("admin/js/device_admin.js",)


# -----------------------
# Interface Admin
# -----------------------
@admin.register(Interface)
class InterfaceAdmin(admin.ModelAdmin):
    list_display = ("name", "device", "status", "mac_address", "endpoint")
    list_filter = ("status", "device")
    search_fields = ("name", "mac_address")

from django.contrib import admin

from .models import VLAN

# -----------------------
# VLAN Admin
# -----------------------
@admin.register(VLAN)
class VLANAdmin(admin.ModelAdmin):
    list_display = ("vlan_id", "name", "site", "subnet", "usage_area")
    list_filter = ("site", "usage_area")
    search_fields = ("vlan_id", "name", "subnet", "description")

