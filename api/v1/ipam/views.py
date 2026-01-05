from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

import ipaddress
from ipam.models import VRF, Prefix, IPAddress
from api.v1.ipam.serializers import VRFSerializer, PrefixSerializer, IPAddressSerializer

class VRFViewSet(viewsets.ModelViewSet):
    queryset = VRF.objects.select_related("site").all()
    serializer_class = VRFSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["name", "rd", "site"]
    search_fields = ["name", "rd", "description"]
    ordering_fields = ["name", "rd", "created_at"]

class PrefixViewSet(viewsets.ModelViewSet):
    queryset = Prefix.objects.select_related("vrf", "site").all()
    serializer_class = PrefixSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["vrf", "site", "status", "role"]
    search_fields = ["cidr", "description"]
    ordering_fields = ["cidr", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        length = self.request.query_params.get("length")
        if length and length.isdigit():
            qs = qs.filter(cidr__regex=fr"/{length}$")
        return qs

class IPAddressViewSet(viewsets.ModelViewSet):
    queryset = IPAddress.objects.select_related("prefix", "interface", "interface__device").all()
    serializer_class = IPAddressSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "prefix", "interface", "interface__device"]
    search_fields = ["address", "hostname"]
    ordering_fields = ["address", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        vrf = self.request.query_params.get("vrf")
        if vrf:
            qs = qs.filter(prefix__vrf_id=vrf)
        return qs
