from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from automation.engine.diff_engine import generate_diff
from dcim.models import DeviceConfiguration
from dcim.serializers import DeviceConfigurationSerializer


class DeviceConfigurationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for device configuration backups.
    """

    serializer_class = DeviceConfigurationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = DeviceConfiguration.objects.select_related("device").order_by(
            "-backup_time"
        )
        device_id = self.kwargs.get("device_id")
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        return queryset

    def list(self, request, *args, **kwargs):
        if not self.kwargs.get("device_id"):
            return Response(
                {"detail": "Device identifier is required."},
                status=400,
            )
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def latest(self, request, device_id=None):
        configuration = self.get_queryset().first()
        if not configuration:
            return Response(status=404)
        serializer = self.get_serializer(configuration)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="diff/(?P<other_id>[^/.]+)")
    def diff(self, request, device_id=None, pk=None, other_id=None):
        config = self.get_object()
        other = get_object_or_404(self.get_queryset(), pk=other_id)
        diff_text = generate_diff(other.config_text, config.config_text)
        return Response(
            {
                "from": other.id,
                "to": config.id,
                "diff": diff_text,
            }
        )
