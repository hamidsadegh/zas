from django.contrib import admin
from django.http import HttpResponse
from io import BytesIO
from django import forms
import pandas as pd # pyright: ignore[reportMissingModuleSource, reportMissingImports]
from django.utils.timezone import localtime
from .models import (
    Organization,
    Area,
    Rack,
    DeviceRole,
    Vendor,
    Platform,
    DeviceType,
    Device,
    DeviceConfiguration,
    Interface,
    ModuleType,
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
    list_display = ("name", "site", "height", "description")
    list_filter = ("site",)
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
# Platform Admin
# -----------------------
@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ("name", "vendor", "description")
    list_filter = ("vendor",)
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
# ModuleType Admin
# -----------------------
@admin.register(ModuleType)
class ModuleTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "vendor", "description")
    list_filter = ("vendor",)
    search_fields = ("name",)


# -----------------------
# Inline DeviceConfiguration for DeviceAdmin
# -----------------------
class DeviceConfigurationInline(admin.StackedInline):
    model = DeviceConfiguration
    extra = 0
    readonly_fields = ("last_updated",)


# ------------------------------
# Import Form
# ------------------------------
class ImportExcelForm(forms.Form):
    excel_file = forms.FileField(label="Select Excel file")


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
            "Vendor": device.vendor.name if device.vendor else "-",
            "Device Type": device.device_type.model if device.device_type else "-",
            "Platform": device.platform.name if device.platform else "-",
            "Role": device.role.name if device.role else "-",
            "Status": device.status,
            "Image Version": device.image_version,
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
    list_display = (
        "name",
        "management_ip",
        "status",
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
    )
    list_filter = ("status", "device_type", "vendor", "organization", "area")
    actions = [export_devices_to_excel]
    inlines = [DeviceConfigurationInline]


# -----------------------
# Interface Admin
# -----------------------
@admin.register(Interface)
class InterfaceAdmin(admin.ModelAdmin):
    list_display = ("name", "device", "status", "mac_address", "endpoint")
    list_filter = ("status", "device")
    search_fields = ("name", "mac_address")
