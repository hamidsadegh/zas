from rest_framework.routers import DefaultRouter

from .credentials_views import (
    SiteCredentialViewSet,
    SSHCredentialViewSet,
    SNMPCredentialViewSet,
    HTTPCredentialViewSet,
)

router = DefaultRouter()
router.register(r"credentials", SiteCredentialViewSet)
router.register(r"credentials/ssh", SSHCredentialViewSet)
router.register(r"credentials/snmp", SNMPCredentialViewSet)
router.register(r"credentials/http", HTTPCredentialViewSet)

urlpatterns = router.urls
