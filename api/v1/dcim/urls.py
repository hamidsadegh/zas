from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AreaViewSet,
    DeviceConfigurationViewSet,
    DeviceModuleViewSet,
    DeviceRoleViewSet,
    DeviceTypeViewSet,
    DeviceViewSet,
    InterfaceViewSet,
    RackViewSet,
    SiteViewSet,
    VendorViewSet,
)

router = DefaultRouter()
router.register("sites", SiteViewSet)
router.register("devices", DeviceViewSet, basename="dcim-device")
router.register("areas", AreaViewSet)
router.register("racks", RackViewSet)
router.register("deviceroles", DeviceRoleViewSet)
router.register("vendors", VendorViewSet)
router.register("devicetypes", DeviceTypeViewSet)
router.register("interfaces", InterfaceViewSet)
router.register("modules", DeviceModuleViewSet)
router.register(
    r"devices/(?P<device_id>[^/.]+)/configurations",
    DeviceConfigurationViewSet,
    basename="device-configurations",
)

urlpatterns = [
    path("", include(router.urls)),
]
