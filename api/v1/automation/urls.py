from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AutomationJobViewSet,
    AutomationScheduleViewSet,
    CeleryHealthView,
    DeviceTelemetryViewSet,
    JobRunViewSet,
)

router = DefaultRouter()
router.register(
    "schedules",
    AutomationScheduleViewSet,
    basename="automation-schedule",
)
router.register("jobs", AutomationJobViewSet)
router.register("runs", JobRunViewSet)
router.register("telemetry", DeviceTelemetryViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("celery/health/", CeleryHealthView.as_view(), name="celery-health"),
]
