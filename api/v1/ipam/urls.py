# api/v1/ipam/urls.py
from rest_framework.routers import DefaultRouter
from api.v1.ipam.views import (
    VRFViewSet,
    PrefixViewSet,
    IPAddressViewSet,
)

router = DefaultRouter()
router.register(r"vrfs", VRFViewSet, basename="ipam-vrf")
router.register(r"prefixes", PrefixViewSet, basename="ipam-prefix")
router.register(r"ip-addresses", IPAddressViewSet, basename="ipam-ipaddress")

urlpatterns = router.urls
