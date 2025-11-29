from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from dcim.choices import SITE_CHOICES
from dcim.models import Device, Area, Rack, DeviceRole, Vendor, DeviceType, Interface, DeviceConfiguration, DeviceModule

from ..serializers import (
    AreaSerializer,
    DeviceConfigurationSerializer,
    DeviceModuleSerializer,
    DeviceRoleSerializer,
    DeviceSerializer,
    DeviceTypeSerializer,
    InterfaceSerializer,
    RackSerializer,
    VendorSerializer,
)
from accounts.models.system_settings import SystemSettings
from ..forms.device_forms import OtherSettingsForm, ReachabilitySettingsForm, TacacsSettingsForm
from accounts.services.settings_service import get_reachability_checks, get_system_settings

# -----------------------
# HTML Views
# -----------------------
class DeviceListView(LoginRequiredMixin, ListView):
    model = Device
    template_name = "dcim/templates/dcim/device_list.html"
    context_object_name = "devices"
    paginate_by = 25
    per_page_options = (10, 25, 50, 100)
    site_filter_choices = [("all", "All Sites")] + list(SITE_CHOICES)

    def get_paginate_by(self, queryset):
        per_page = self.request.GET.get("paginate_by")
        if per_page and per_page.isdigit():
            per_page = int(per_page)
            if per_page in self.per_page_options:
                self.current_paginate_by = per_page
                return per_page
        self.current_paginate_by = self.paginate_by
        return self.paginate_by
    
    def get_queryset(self):
        queryset = Device.objects.select_related(
            "vendor", "device_type", "area", "rack", "runtime"
        ).order_by("name")

        site = self.request.GET.get("site", "all")
        valid_site_keys = {choice[0] for choice in self.site_filter_choices}
        if site not in valid_site_keys:
            site = "all"
        self.current_site_filter = site
        if site != "all":
            queryset = queryset.filter(site=site)

        search = self.request.GET.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(management_ip__icontains=search)
                | Q(serial_number__icontains=search)
                | Q(image_version__icontains=search)
                | Q(device_type__model__icontains=search)
                | Q(vendor__name__icontains=search)
                | Q(area__name__icontains=search)
                | Q(rack__name__icontains=search)
                | Q(site__icontains=search)
            ).distinct()

        sort = self.request.GET.get("sort", "name")
        if sort.lstrip("-") in [
            "name",
            "management_ip",
            "status",
            "device_type__model",
            "serial_number",
            "area__name",
            "rack__name",
            "site",
            "image_version",
        ]:
            queryset = queryset.order_by(sort)

        return queryset


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['sort_field'] = self.request.GET.get('sort', 'name')
        context['paginate_by'] = getattr(self, "current_paginate_by", self.paginate_by)
        context['site_choices'] = self.site_filter_choices
        context['site_filter'] = getattr(self, "current_site_filter", "all")
        context['per_page_options'] = self.per_page_options
        settings_obj = get_system_settings()
        context['reachability_checks'] = get_reachability_checks(settings_obj)
        return context

class DeviceDetailView(LoginRequiredMixin, DetailView):
    model = Device
    template_name = "dcim/device_detail.html"
    context_object_name = "device"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        device = self.get_object()

        # Get search and sort params for interfaces
        search_query = self.request.GET.get('search', '')
        sort_field = self.request.GET.get('sort', 'name')

        interfaces = device.interfaces.all()

        # Search interfaces
        if search_query:
            interfaces = interfaces.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(ip_address__icontains=search_query) |
                Q(mac_address__icontains=search_query) |
                Q(endpoint__icontains=search_query)
            )

        # Allow only safe fields to sort
        allowed_sort_fields = ['name', 'status', 'ip_address', 'mac_address', 'speed']
        if sort_field not in allowed_sort_fields:
            sort_field = 'name'

        interfaces = interfaces.order_by(sort_field)

        context['interfaces'] = interfaces
        context['search_query'] = search_query
        context['sort_field'] = sort_field
        context['reachability_checks'] = get_reachability_checks(get_system_settings())
        return context


class AreaListView(LoginRequiredMixin, ListView):
    model = Area
    template_name = "dcim/templates/dcim/area_list.html"
    context_object_name = "areas"


class AreaDetailView(LoginRequiredMixin, DetailView):
    model = Area
    template_name = "dcim/templates/dcim/area_detail.html"
    context_object_name = "area"


class RackListView(LoginRequiredMixin, ListView):
    model = Rack
    template_name = "dcim/templates/dcim/rack_list.html"
    context_object_name = "racks"


@login_required
def devices_by_area(request, area_id):
    area = get_object_or_404(Area, id=area_id)
    devices = Device.objects.filter(area=area)
    return render(request, "dcim/templates/dcim/devices_by_area.html", {"area": area, "devices": devices})


@login_required
def racks_by_area(request):
    area_id = request.GET.get("area_id")
    racks = Rack.objects.filter(area_id=area_id).values("id", "name")
    return JsonResponse({"results": list(racks)})


@login_required
def racks_for_area(request):
    area_id = request.GET.get("area")
    racks = Rack.objects.none()
    if area_id:
        racks = Rack.objects.filter(area_id=area_id).order_by("name")
    data = [{"id": rack.id, "name": rack.name} for rack in racks]
    return JsonResponse({"results": data})


# -----------------------
# DRF API ViewSets
# -----------------------
class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.select_related(
        "organization",
        "area",
        "vendor",
        "device_type",
        "role",
        "rack",
        "runtime",
    ).prefetch_related("modules__vendor")
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "management_ip", "serial_number", "inventory_number", "site"]
    ordering_fields = ["name", "management_ip", "created_at"]


class AreaViewSet(viewsets.ModelViewSet):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "organization"]


class RackViewSet(viewsets.ModelViewSet):
    queryset = Rack.objects.all()
    serializer_class = RackSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "area__name"]
    ordering_fields = ["name", "area"]

    def get_queryset(self):
        queryset = Rack.objects.all()
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


class DeviceConfigurationViewSet(viewsets.ModelViewSet):
    queryset = DeviceConfiguration.objects.all()
    serializer_class = DeviceConfigurationSerializer
    permission_classes = [IsAuthenticated]


class DeviceModuleViewSet(viewsets.ModelViewSet):
    queryset = DeviceModule.objects.select_related("device", "vendor")
    serializer_class = DeviceModuleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "serial_number", "device__name", "vendor__name"]
    ordering_fields = ["name", "serial_number", "device"]
