from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views
from dcim.views import device_views
from accounts.views.system_setting_view import SystemSettingsView
from rest_framework import routers


# -----------------------
# DRF Router
# -----------------------
router = routers.DefaultRouter()
router.register(r"sites", device_views.SiteViewSet)
router.register(r"devices", device_views.DeviceViewSet)
router.register(r"areas", device_views.AreaViewSet)
router.register(r"racks", device_views.RackViewSet)
router.register(r"deviceroles", device_views.DeviceRoleViewSet)
router.register(r"vendors", device_views.VendorViewSet)
router.register(r"devicetypes", device_views.DeviceTypeViewSet)
router.register(r"interfaces", device_views.InterfaceViewSet)
router.register(r"deviceconfigurations", device_views.DeviceConfigurationViewSet)
router.register(r"modules", device_views.DeviceModuleViewSet)

# -----------------------
# HTML Views URL patterns
# -----------------------
html_patterns = [
    path("devices/", device_views.DeviceListView.as_view(), name="device_list"),
    path("devices/<uuid:pk>/", device_views.DeviceDetailView.as_view(), name="device_detail"),
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
    path("", include("core.urls")),             # Core app URLs (dashboard as home)
    path("admin/", admin.site.urls),            # /admin/login/ is default login
    path("api/", include(router.urls)),         # DRF API
    path("", include(html_patterns)),           # HTML views
    path("dcim/", include("dcim.urls")),
    path("api-auth/", include("rest_framework.urls")),  # DRF login/logout for browsable API
    path("api/automation/", include("automation.urls")),

]
