from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from asset import views as asset_views
from dcim.views import device_views
from accounts.views.system_setting_view import SystemSettingsView

# -----------------------
# HTML Views URL patterns
# -----------------------
html_patterns = [
    path("devices/", device_views.DeviceListView.as_view(), name="device_list"),
    path("devices/export/", device_views.device_export, name="device_export"),
    path("devices/<uuid:pk>/decommission/", device_views.device_decommission, name="device_decommission"),
    path("devices/<uuid:pk>/", device_views.DeviceDetailView.as_view(), name="device_detail"),
    path("inventory/", device_views.inventory_hub, name="inventory"),
    path("inventory/production/", device_views.inventory_list, name="inventory_production"),
    path("inventory/storage/", asset_views.storage_inventory_list, name="inventory_storage"),
    path("inventory/storage/add/", asset_views.InventoryItemAddView.as_view(), name="inventory_storage_add"),
    path("inventory/storage/<uuid:pk>/edit/", asset_views.InventoryItemUpdateView.as_view(), name="inventory_storage_edit"),
    path("inventory/storage/<uuid:pk>/delete/", asset_views.InventoryItemDeleteView.as_view(), name="inventory_storage_delete"),
    path("inventory/storage/export/", asset_views.storage_inventory_export, name="inventory_storage_export"),
    path("inventory/storage/import/", asset_views.storage_inventory_import, name="inventory_storage_import"),
    path("inventory/export/", device_views.inventory_export, name="inventory_export"),
    path("areas/", device_views.AreaListView.as_view(), name="area_list"),
    path("areas/<uuid:pk>/", device_views.AreaDetailView.as_view(), name="area_detail"),
    path("racks/", device_views.RackListView.as_view(), name="rack_list"),
    path("areas/<uuid:area_id>/devices/", device_views.devices_by_area, name="devices_by_area"),
    path("racks/for-area/", device_views.racks_for_area, name="racks_for_area"),
    path("areas/for-site/", device_views.areas_for_site, name="areas_for_site"),
    path("system-settings/", SystemSettingsView.as_view(), name="system_settings"),
]

# -----------------------
# Main URL patterns
# -----------------------
urlpatterns = [
    path("logout/", auth_views.LogoutView.as_view(next_page="/admin/login/"), name="logout"),
    path("", include("core.urls")),                     # Core app URLs (dashboard as home)
    path("admin/", admin.site.urls),                    # /admin/login/ is default login
    path("api/", include("api.urls")),                  # DRF API (versioned)
    path("", include(html_patterns)),                   # HTML views
    path("automation/", include(("automation.urls", "automation"), namespace="automation")),
    path("dcim/", include("dcim.urls")),                # DCIM app URLs
    path("ipam/", include(("ipam.urls", "ipam"), namespace="ipam")),
    path("api-auth/", include("rest_framework.urls")),  # DRF login/logout for browsable API
    path("", include(("network.urls", "network"), namespace="network")),
]
