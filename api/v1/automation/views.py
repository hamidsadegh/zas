from celery import current_app
from celery.exceptions import CeleryError
from django_celery_beat.models import PeriodicTask
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from automation.models import (
    AutomationJob,
    AutomationSchedule,
    DeviceTelemetry,
    JobRun,
)
from .serializers import (
    AutomationJobSerializer,
    AutomationScheduleSerializer,
    DeviceTelemetrySerializer,
    JobRunSerializer,
)


class AutomationScheduleViewSet(viewsets.ModelViewSet):
    queryset = AutomationSchedule.objects.all().order_by("name")
    serializer_class = AutomationScheduleSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"], url_path="run")
    def run_now(self, request, pk=None):
        schedule = self.get_object()
        try:
            async_result = current_app.send_task(schedule.task_name)
        except CeleryError as exc:
            return Response(
                {"status": "error", "detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(
            {
                "status": "scheduled",
                "task": schedule.task_name,
                "celery_id": async_result.id,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class CeleryHealthView(APIView):
    """
    Simple Celery health check:
    - Broker connectivity
    - Known automation tasks
    - Periodic tasks count
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        info = {
            "broker_ok": False,
            "workers_responding": [],
            "registered_tasks": [],
            "periodic_tasks": [],
        }
        tasks = sorted(t for t in current_app.tasks.keys() if t.startswith("automation."))
        info["registered_tasks"] = tasks

        pts = PeriodicTask.objects.all().order_by("name")
        info["periodic_tasks"] = [
            {
                "name": pt.name,
                "task": pt.task,
                "enabled": pt.enabled,
                "last_run_at": pt.last_run_at,
                "total_run_count": pt.total_run_count,
            }
            for pt in pts
        ]

        try:
            inspector = current_app.control.inspect(timeout=1.0)
            ping = inspector.ping() or {}
            info["workers_responding"] = list(ping.keys())
            info["broker_ok"] = bool(ping)
        except Exception as exc:  # pragma: no cover - diagnostics only
            info["broker_ok"] = False
            info["error"] = str(exc)

        status_code = (
            status.HTTP_200_OK if info["broker_ok"] else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(info, status=status_code)


class AutomationJobViewSet(viewsets.ModelViewSet):
    queryset = AutomationJob.objects.all()
    serializer_class = AutomationJobSerializer
    permission_classes = [IsAuthenticated]


class JobRunViewSet(viewsets.ModelViewSet):
    queryset = JobRun.objects.all().select_related("job")
    serializer_class = JobRunSerializer
    permission_classes = [IsAuthenticated]


class DeviceTelemetryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeviceTelemetry.objects.select_related("device")
    serializer_class = DeviceTelemetrySerializer
    permission_classes = [IsAuthenticated]
