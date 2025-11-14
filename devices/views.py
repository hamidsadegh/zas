from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from .models import (
    Device,
    Area,
    Rack,
    DeviceRole,
    Vendor,
    DeviceType,
    Interface,
    DeviceConfiguration,
)
from .serializers import (
    DeviceSerializer,
    AreaSerializer,
    RackSerializer,
    DeviceRoleSerializer,
    VendorSerializer,
    DeviceTypeSerializer,
    InterfaceSerializer,
    DeviceConfigurationSerializer
)
from accounts.models import SystemSettings
from .forms import SystemSettingsForm

# -----------------------
# HTML Views
# -----------------------
class DeviceListView(LoginRequiredMixin, ListView):
    model = Device
    template_name = "devices/device_list.html"
    context_object_name = "devices"
    paginate_by = 25
    per_page_options = (10, 25, 50, 100)

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
            "vendor", "device_type", "area"
        ).order_by("name")

        site = self.request.GET.get("site", Device.SITE_CHOICES[0][0])
        site_choices = dict(Device.SITE_CHOICES)
        if site not in site_choices:
            site = Device.SITE_CHOICES[0][0]
        self.current_site_filter = site
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
            ).distinct()

        sort = self.request.GET.get("sort", "name")
        if sort.lstrip("-") in [
            "name",
            "management_ip",
            "status",
            "device_type__model",
            "serial_number",
            "area__name",
            "image_version",
        ]:
            queryset = queryset.order_by(sort)

        return queryset


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['sort_field'] = self.request.GET.get('sort', 'name')
        context['paginate_by'] = getattr(self, "current_paginate_by", self.paginate_by)
        context['site_choices'] = Device.SITE_CHOICES
        context['site_filter'] = getattr(self, "current_site_filter", Device.SITE_CHOICES[0][0])
        context['per_page_options'] = self.per_page_options
        return context

class DeviceDetailView(LoginRequiredMixin, DetailView):
    model = Device
    template_name = "devices/device_detail.html"
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
        return context


class AreaListView(LoginRequiredMixin, ListView):
    model = Area
    template_name = "devices/area_list.html"
    context_object_name = "areas"


class AreaDetailView(LoginRequiredMixin, DetailView):
    model = Area
    template_name = "devices/area_detail.html"
    context_object_name = "area"


class RackListView(LoginRequiredMixin, ListView):
    model = Rack
    template_name = "devices/rack_list.html"
    context_object_name = "racks"


def devices_by_area(request, area_id):
    area = get_object_or_404(Area, id=area_id)
    devices = Device.objects.filter(area=area)
    return render(request, "devices/devices_by_area.html", {"area": area, "devices": devices})


# -----------------------
# DRF API ViewSets
# -----------------------
class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
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
    search_fields = ["name", "site__name"]
    ordering_fields = ["name", "site"]


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

# -----------------------
# Home View
# -----------------------
@login_required
def home(request):
    """Home dashboard page with quick health metrics"""
    device_stats = Device.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(status="active")),
        inactive=Count("id", filter=Q(status="inactive")),
        maintenance=Count("id", filter=Q(status="maintenance")),
        unknown=Count("id", filter=Q(status="unknown")),
    )

    interface_stats = Interface.objects.aggregate(
        total=Count("id"),
        up=Count("id", filter=Q(status="up")),
        down=Count("id", filter=Q(status="down")),
        disabled=Count("id", filter=Q(status="disabled")),
    )

    recent_devices = (
        Device.objects.select_related("area", "vendor", "device_type")
        .order_by("-created_at")[:5]
    )

    recent_checks = (
        Device.objects.exclude(last_check__isnull=True)
        .order_by("-last_check")[:5]
    )

    top_vendors = (
        Vendor.objects.annotate(device_count=Count("devices"))
        .order_by("-device_count")[:5]
    )

    context = {
        "device_stats": device_stats,
        "interface_stats": interface_stats,
        "recent_devices": recent_devices,
        "recent_checks": recent_checks,
        "top_vendors": top_vendors,
    }
    return render(request, "devices/home.html", context)


class SystemSettingsView(LoginRequiredMixin, View):
    template_name = "devices/system_settings.html"

    def get_settings(self):
        return SystemSettings.get()

    def get(self, request):
        form = SystemSettingsForm(instance=self.get_settings())
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        settings_obj = self.get_settings()
        form = SystemSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "TACACS+ settings saved.")
            return redirect("system_settings")
        messages.error(request, "Please fix the highlighted errors.")
        return render(request, self.template_name, {"form": form})
