from django.contrib import admin
from django.http import HttpResponse
from django.contrib.admin import SimpleListFilter
from django.urls import reverse
from io import BytesIO
from django import forms
import pandas as pd  # pyright: ignore[reportMissingModuleSource, reportMissingImports]
from django.utils.timezone import localtime

from .models import (
    Organization,
    Site,
    Area,
    Rack,
    DeviceRole,
    Vendor,
    DeviceType,
    Device,
    DeviceConfiguration,
    Interface,
    DeviceModule,
    Tag,
)

# -----------------------
# Organization Admin
# -----------------------
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "created_at", "updated_at")
    search_fields = ("name",)


# -----------------------
# Site Admin
# -----------------------
@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "description", "created_at")
    list_filter = ("organization",)
    search_fields = ("name", "organization__name")
    ordering = ("organization__name", "name")


class AreaAdminForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        parent = cleaned_data.get("parent")
        site = cleaned_data.get("site")
        if parent and site and parent.site_id != site.id:
            self.add_error(
                "parent",
                "Parent area must belong to the same site as this area.",
            )
        return cleaned_data


# -----------------------
# Area Admin (hierarchical)
# -----------------------
@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    form = AreaAdminForm
    list_display = ("name", "parent", "site")
    list_filter = ("site",)
    search_fields = ("name", "site__name")
    ordering = ("site__name", "parent__name", "name")


# -----------------------
# Rack Admin
# -----------------------
@admin.register(Rack)
class RackAdmin(admin.ModelAdmin):
    list_display = ("name", "area", "u_height", "description")
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
    list_display = ("model", "vendor",)
    list_filter = ("vendor",)
    search_fields = ("model",)


# -----------------------
# DeviceModule Admin
# -----------------------
@admin.register(DeviceModule)
class DeviceModuleAdmin(admin.ModelAdmin):
    list_display = ("name", "device", "serial_number", "vendor", "description")
    list_filter = ("vendor", "device")
    search_fields = ("name",)


@admin.register(DeviceConfiguration)
class DeviceConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        "device",
        "collected_at",
        "source",
        "success",
        "short_hash",
    )

    readonly_fields = (
        "device",
        "config_text",
        "collected_at",
        "collected_by",
        "source",
        "config_hash",
        "previous",
        "success",
        "error_message",
        "created_at",
    )

    ordering = ("-collected_at",)
    search_fields = ("device__name", "config_hash")
    list_filter = ("source", "success")

    def short_hash(self, obj):
        return obj.config_hash[:12]

    short_hash.short_description = "Config hash"


# -----------------------
# Inline DeviceConfiguration for DeviceAdmin
# -----------------------
class DeviceConfigurationInline(admin.TabularInline):
    model = DeviceConfiguration
    extra = 0
    can_delete = False

    readonly_fields = (
        "collected_at",
        "source",
        "success",
    )

    fields = (
        "collected_at",
        "source",
        "success",
    )


class DeviceModuleInline(admin.TabularInline):
    model = DeviceModule
    extra = 1
    fields = ("name", "serial_number", "vendor", "description")
    autocomplete_fields = ("vendor",)


# -----------------------
# Tag Admin
# -----------------------
class TagFilter(admin.SimpleListFilter):
    title = "Tag"
    parameter_name = "tag"

    def lookups(self, request, model_admin):
        return [(tag.id, tag.name) for tag in Tag.objects.all()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(tags__id=self.value())
        return queryset
    
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "color")
    search_fields = ("name",)

# ------------------------------
# Import Form
# ------------------------------
class ImportExcelForm(forms.Form):
    excel_file = forms.FileField(label="Select Excel file")


from django import forms
from django.urls import reverse
from .models import Area, Device, Rack, Site


class DeviceAdminForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._set_widget_attr("site", "data-areas-url", reverse("areas_for_site"))
        self._set_widget_attr("area", "data-racks-url", reverse("racks_for_area"))

        site_id = self._current_site_id()
        area_field = self.fields.get("area")
        rack_field = self.fields.get("rack")
        area_id = self._current_area_id()
        area_widget = self._base_widget("area")
        rack_widget = self._base_widget("rack")

        if site_id:
            qs = Area.objects.filter(site_id=site_id)

            # IMPORTANT: always include current area on change form
            if area_id:
                qs = qs | Area.objects.filter(pk=area_id)

            area_field.queryset = qs.distinct()

            if area_widget:
                area_widget.attrs.pop("disabled", None)

        else:
            area_field.queryset = Area.objects.none()
            area_field.help_text = "Areas will appear after selecting a Site."
            if area_widget:
                area_widget.attrs["disabled"] = "disabled"

        if area_id:
            rack_field.queryset = Rack.objects.filter(area_id=area_id)
            if rack_widget:
                rack_widget.attrs.pop("disabled", None)
        else:
            rack_field.queryset = Rack.objects.none()
            rack_field.help_text = "Racks will appear after selecting an Area."
            if rack_widget:
                rack_widget.attrs["disabled"] = "disabled"

        if area_widget:
            area_widget.attrs["data-current-value"] = str(area_id) if area_id else ""
        current_rack_id = self._current_rack_id()
        if rack_widget:
            rack_widget.attrs["data-current-value"] = str(current_rack_id) if current_rack_id else ""

    class Media:
        js = ("dcim/js/device_location_admin.js",)

    # Helpers — determine selected area/rack from POST or instance
    def _current_site_id(self):
        """Resolve site from POST data or instance."""
        if self.data.get("site"):
            return self.data.get("site")

        if self.instance and self.instance.pk:
            return self.instance.site_id

        return None

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

    def _base_widget(self, field_name):
        field = self.fields.get(field_name)
        if not field:
            return None
        widget = field.widget
        return getattr(widget, "widget", widget)

    def _set_widget_attr(self, field_name, attr, value):
        widget = self._base_widget(field_name)
        if widget:
            widget.attrs[attr] = value


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
            "Organization": device.site.organization.name if device.site else "-",
            "Site": device.site.name if device.site else "-",
            "Area": str(device.area) if device.area else "-",
            "Rack": device.rack.name if device.rack else "-",
            "Device Type": device.device_type.model if device.device_type else "-",
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
        "tag_list",
    )
    search_fields = (
        "name",
        "management_ip",
        "serial_number",
        "inventory_number",
        "area__name",
        "site__name",
        "tags__name",
        "device_type__model",
        "device_type__vendor",
        "site__organization__name",
    )
    list_filter = (
        "status",
        "site",
        "area",
        "device_type",
        "device_type__vendor",
        "site__organization",
        TagFilter,
    )
    actions = [export_devices_to_excel]
    inlines = [DeviceModuleInline, DeviceConfigurationInline]

    class Media:
        js = ("admin/js/device_admin.js",)

    @admin.display(description="Tags")
    def tag_list(self, obj):
        return ", ".join([t.name for t in obj.tags.all()])

    @admin.display(description="Organization", ordering="site__organization__name")
    def organization(self, obj):
        if obj.site:
            return obj.site.organization
        return "-"


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
