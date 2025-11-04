from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from devices import views as device_views
from rest_framework import routers


# -----------------------
# DRF Router
# -----------------------
router = routers.DefaultRouter()
router.register(r"devices", device_views.DeviceViewSet)
router.register(r"areas", device_views.AreaViewSet)
router.register(r"racks", device_views.RackViewSet)
router.register(r"deviceroles", device_views.DeviceRoleViewSet)
router.register(r"vendors", device_views.VendorViewSet)
router.register(r"platforms", device_views.PlatformViewSet)
router.register(r"devicetypes", device_views.DeviceTypeViewSet)
router.register(r"interfaces", device_views.InterfaceViewSet)
router.register(r"deviceconfigurations", device_views.DeviceConfigurationViewSet)

# -----------------------
# HTML Views URL patterns
# -----------------------
html_patterns = [
    path("devices/", device_views.DeviceListView.as_view(), name="device_list"),
    path("devices/<int:pk>/", device_views.DeviceDetailView.as_view(), name="device_detail"),
    path("areas/", device_views.AreaListView.as_view(), name="area_list"),
    path("areas/<int:pk>/", device_views.AreaDetailView.as_view(), name="area_detail"),
    path("racks/", device_views.RackListView.as_view(), name="rack_list"),
    path("areas/<int:area_id>/devices/", device_views.devices_by_area, name="devices_by_area"),
    path('', device_views.home, name='home'),
]

# -----------------------
# Main URL patterns
# -----------------------
urlpatterns = [
    path("", lambda request: redirect("device_list"), name="home"),
    path("admin/", admin.site.urls),            # /admin/login/ is default login
    path("api/", include(router.urls)),         # DRF API
    path("", include(html_patterns)),           # HTML views
    path("api-auth/", include("rest_framework.urls")),  # DRF login/logout for browsable API
    path("api/automation/", include("automation.urls")),

]
