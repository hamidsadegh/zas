from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from ipam.models import VRF, Prefix, IPAddress
from api.v1.ipam.serializers import VRFSerializer, PrefixSerializer, IPAddressSerializer

class VRFViewSet(viewsets.ModelViewSet):
    queryset = VRF.objects.all()
    serializer_class = VRFSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["name", "rd"]
    search_fields = ["name", "rd", "description"]
    ordering_fields = ["name", "rd", "created_at"]

class PrefixViewSet(viewsets.ModelViewSet):
    queryset = Prefix.objects.select_related("vrf").all()
    serializer_class = PrefixSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["vrf", "status", "role", "is_pool"]
    search_fields = ["prefix", "description"]
    ordering_fields = ["prefix", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        contains = self.request.query_params.get("contains")
        within = self.request.query_params.get("within")
        family = self.request.query_params.get("family")

        # These assume prefix stored in a Postgres-friendly type (cidr/inet) or as string.
        # If it's string, you'll need Python filtering or custom SQL; with cidr it’s trivial.
        if family in ("4", "6"):
            qs = qs.filter(prefix__family=int(family))  # works if you store as IPNetwork-like type
        if contains:
            qs = qs.filter(prefix__net_contains=contains)  # Postgres inet/cidr ops (django-netfields or custom)
        if within:
            qs = qs.filter(prefix__net_contained=within)
        return qs

class IPAddressViewSet(viewsets.ModelViewSet):
    queryset = IPAddress.objects.select_related("vrf").all()
    serializer_class = IPAddressSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["vrf", "status"]
    search_fields = ["address", "dns_name", "description"]
    ordering_fields = ["address", "created_at"]
