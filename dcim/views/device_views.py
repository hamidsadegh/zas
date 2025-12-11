import uuid

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from dcim.models import (
    Area,
    Device,
    DeviceConfiguration,
    Rack,
    Site,
)
from automation.engine.diff_engine import generate_diff, generate_visual_diff
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
            "vendor",
            "device_type",
            "area",
            "rack",
            "runtime",
            "site",
            "site__organization",
        ).order_by("name")

        self.site_filter_choices = self._site_filter_options()
        site = self.request.GET.get("site", "all")
        valid_site_keys = {choice[0] for choice in self.site_filter_choices}
        if site not in valid_site_keys:
            site = "all"
        self.current_site_filter = site
        if site != "all":
            queryset = queryset.filter(site_id=site)

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
                | Q(site__name__icontains=search)
                | Q(site__organization__name__icontains=search)
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
            "site__name",
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

    def _site_filter_options(self):
        choices = [("all", "All Sites")]
        for site in Site.objects.select_related("organization").order_by("name"):
            label = f"{site.name} ({site.organization.name})"
            choices.append((str(site.id), label))
        return choices

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
        latest_config = (
            DeviceConfiguration.objects.filter(device=device)
            .order_by("-backup_time")
            .first()
        )
        if latest_config:
            preview_lines = (latest_config.config_text or "").splitlines()
            context["latest_config"] = latest_config
            context["latest_config_preview"] = "\n".join(preview_lines[:20])
        else:
            context["latest_config"] = None
            context["latest_config_preview"] = ""
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
    racks = Rack.objects.none()
    try:
        if area_id:
            uuid.UUID(str(area_id))
            racks = Rack.objects.filter(area_id=area_id)
    except (ValueError, TypeError):
        racks = Rack.objects.none()
    return JsonResponse({"results": list(racks)})


@login_required
def racks_for_area(request):
    area_id = request.GET.get("area")
    racks = Rack.objects.none()
    if area_id:
        try:
            uuid.UUID(str(area_id))
            racks = Rack.objects.filter(area_id=area_id).order_by("name")
        except (ValueError, TypeError):
            racks = Rack.objects.none()
    data = [{"id": rack.id, "name": rack.name} for rack in racks]
    return JsonResponse({"results": data})


@login_required
def areas_for_site(request):
    site_id = request.GET.get("site")
    areas = Area.objects.none()
    if site_id:
        try:
            uuid.UUID(str(site_id))
            areas = Area.objects.filter(site_id=site_id).order_by("name")
        except (ValueError, TypeError):
            areas = Area.objects.none()
    data = [{"id": area.id, "name": area.name} for area in areas]
    return JsonResponse({"results": data})


@login_required
def device_configuration_history(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    queryset = DeviceConfiguration.objects.filter(device=device).order_by("-backup_time")
    configurations = list(queryset)
    config_rows = []
    previous = None
    for config in configurations:
        config_rows.append({"config": config, "previous": previous})
        previous = config
    focus_id = request.GET.get("focus")
    selected_config = None
    if focus_id:
        try:
            uuid.UUID(str(focus_id))
            selected_config = queryset.filter(id=focus_id).first()
        except (ValueError, TypeError):
            selected_config = None

    if request.method == "POST":
        selected = request.POST.getlist("compare")
        if len(selected) == 2:
            return redirect(
                "device_configuration_diff",
                device_id=device.id,
                config_id=selected[0],
                other_id=selected[1],
            )
        messages.error(request, "Select two configuration backups to compare.")

    context = {
        "device": device,
        "config_rows": config_rows,
        "selected_config": selected_config,
    }
    return render(request, "dcim/device_configuration_history.html", context)


@login_required
def device_configuration_diff(request, device_id, config_id, other_id):
    device = get_object_or_404(Device, id=device_id)
    primary = get_object_or_404(
        DeviceConfiguration, id=config_id, device=device
    )
    secondary = get_object_or_404(
        DeviceConfiguration, id=other_id, device=device
    )
    diff_text = generate_diff(secondary.config_text, primary.config_text)
    visual = generate_visual_diff(secondary.config_text, primary.config_text)
    context = {
        "device": device,
        "primary_config": primary,
        "secondary_config": secondary,
        "diff": diff_text,
        "visual_diff": visual,
    }
    return render(request, "dcim/device_configuration_diff.html", context)


@login_required
def device_configuration_visual_diff(request, device_id, config_id, other_id):
    device = get_object_or_404(Device, id=device_id)
    primary = get_object_or_404(
        DeviceConfiguration, id=config_id, device=device
    )
    secondary = get_object_or_404(
        DeviceConfiguration, id=other_id, device=device
    )
    visual = generate_visual_diff(secondary.config_text, primary.config_text)
    paired = list(
        zip(
            visual["left_lines"],
            visual["left_classes"],
            visual["right_lines"],
            visual["right_classes"],
        )
    )
    context = {
        "device": device,
        "primary_config": primary,
        "secondary_config": secondary,
        "diff_rows": paired,
    }
    return render(
        request,
        "dcim/device_configuration_visual_diff.html",
        context,
    )
