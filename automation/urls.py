from rest_framework import routers
from .views import AutomationJobViewSet, JobRunViewSet, DeviceTelemetryViewSet

router = routers.DefaultRouter()
router.register(r'jobs', AutomationJobViewSet)
router.register(r'runs', JobRunViewSet)
router.register(r'telemetry', DeviceTelemetryViewSet)

urlpatterns = router.urls
