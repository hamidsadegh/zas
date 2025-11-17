from rest_framework import viewsets
from .models import AutomationJob, JobRun, DeviceTelemetry
from .serializers import (
    AutomationJobSerializer, JobRunSerializer, DeviceTelemetrySerializer
)

class AutomationJobViewSet(viewsets.ModelViewSet):
    queryset = AutomationJob.objects.all()
    serializer_class = AutomationJobSerializer

class JobRunViewSet(viewsets.ModelViewSet):
    queryset = JobRun.objects.all().select_related('job')
    serializer_class = JobRunSerializer

class DeviceTelemetryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeviceTelemetry.objects.all().select_related('device')
    serializer_class = DeviceTelemetrySerializer
