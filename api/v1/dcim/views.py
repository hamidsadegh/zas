from django.shortcuts import get_object_or_404
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from automation.engine.diff_engine import generate_diff
from dcim.models import (
    Area,
    Device,
    DeviceConfiguration,
    DeviceModule,
    DeviceRole,
    DeviceType,
    Interface,
    Rack,
    Site,
    Vendor,
)
from .serializers import (
    AreaSerializer,
    DeviceConfigurationSerializer,
    DeviceModuleSerializer,
    DeviceRoleSerializer,
    DeviceSerializer,
    DeviceTypeSerializer,
    InterfaceSerializer,
    RackSerializer,
    SiteSerializer,
    VendorSerializer,
)


class SiteViewSet(viewsets.ModelViewSet):
    queryset = Site.objects.select_related("organization")
    serializer_class = SiteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "organization__name"]
    ordering_fields = ["name", "organization__name"]


class DeviceViewSet(viewsets.ModelViewSet):
    queryset = (
        Device.objects.select_related(
            "site",
            "site__organization",
            "area",
            "device_type__vendor",
            "device_type",
            "role",
            "rack",
            "runtime",
        )
        .prefetch_related("modules__vendor")
        .all()
    )
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "name",
        "management_ip",
        "serial_number",
        "inventory_number",
        "site__name",
        "site__organization__name",
    ]
    ordering_fields = ["name", "management_ip", "created_at", "site__name"]


class AreaViewSet(viewsets.ModelViewSet):
    queryset = Area.objects.select_related("site", "site__organization", "parent")
    serializer_class = AreaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "site__name"]
    ordering_fields = ["name", "site__name"]


class RackViewSet(viewsets.ModelViewSet):
    queryset = Rack.objects.select_related("area", "area__site")
    serializer_class = RackSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "area__name", "area__site__name"]
    ordering_fields = ["name", "area", "area__site__name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        area_id = self.request.query_params.get("area")
        if area_id:
            queryset = queryset.filter(area_id=area_id)
        return queryset


class DeviceRoleViewSet(viewsets.ModelViewSet):
    queryset = DeviceRole.objects.all()
    serializer_class = DeviceRoleSerializer
    permission_classes = [IsAuthenticated]


class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [IsAuthenticated]


class DeviceTypeViewSet(viewsets.ModelViewSet):
    queryset = DeviceType.objects.all()
    serializer_class = DeviceTypeSerializer
    permission_classes = [IsAuthenticated]


class InterfaceViewSet(viewsets.ModelViewSet):
    queryset = Interface.objects.all()
    serializer_class = InterfaceSerializer
    permission_classes = [IsAuthenticated]


class DeviceModuleViewSet(viewsets.ModelViewSet):
    queryset = DeviceModule.objects.select_related("device", "vendor")
    serializer_class = DeviceModuleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "serial_number", "device__name", "vendor__name"]
    ordering_fields = ["name", "serial_number", "device"]


class DeviceConfigurationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DeviceConfigurationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = DeviceConfiguration.objects.select_related("device").order_by(
            "-collected_at"
        )
        device_id = self.kwargs.get("device_id")
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        return queryset

    def list(self, request, *args, **kwargs):
        if not self.kwargs.get("device_id"):
            return Response({"detail": "Device identifier is required."}, status=400)
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
