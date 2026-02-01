import re
import uuid

from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Case, IntegerField, Q, Value, When
from dcim.choices import InterfaceStatusChoices
from dcim.models import (
    Area,
    Device,
    DeviceConfiguration,
    Interface,
    Rack,
    Tag,
    Site,
)
from automation.engine.diff_engine import generate_diff, generate_visual_diff
from accounts.services.settings_service import get_reachability_checks, get_system_settings

from openpyxl import Workbook

PREVIEW_LIMIT = 10
PER_PAGE_OPTIONS = (10, 25, 50, 100, 200)


def _natural_sort_key(value):
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", value or "")
    ]


def _get_paginate_by(request, default=25):
    per_page = request.GET.get("paginate_by")
    if per_page and per_page.isdigit():
        per_page = int(per_page)
        if per_page in PER_PAGE_OPTIONS:
            return per_page
    return default


def _build_inventory_rows(search_query):
    devices = (
        Device.objects.select_related(
            "device_type",
            "device_type__vendor",
            "site",
            "area",
            "rack",
        )
        .prefetch_related("modules", "tags")
        .all()
    )

    rows = []
    query = (search_query or "").lower().strip()

    def device_matches(device):
        if not query:
            return True
        haystack = " ".join(
            filter(
                None,
                [
                    device.name or "",
                    device.serial_number or "",
                    device.inventory_number or "",
                    device.site.name if device.site else "",
                    device.area.name if device.area else "",
                    device.rack.name if device.rack else "",
                ],
            )
        ).lower()
        return query in haystack

    def module_matches(module):
        if not query:
            return True
        haystack = " ".join(
            filter(
                None,
                [
                    module.name or "",
                    module.serial_number or "",
                    module.description or "",
                ],
            )
        ).lower()
        return query in haystack

    for device in devices:
        device_match = device_matches(device)
        if device.rack:
            device_location = f"{device.rack.area} \u2192 {device.rack.name}"
        elif device.area:
            device_location = str(device.area)
        elif device.site:
            device_location = device.site.name
        else:
            device_location = ""
        modules = list(device.modules.all())
        if not modules:
            if device_match or not query:
                rows.append(
                    {
                        "device": device,
                        "device_name": device.name or "",
                        "device_serial": device.serial_number or "",
                        "device_site_id": str(device.site.id) if device.site else "",
                        "device_site": device.site.name if device.site else "",
                        "device_area": device.area.name if device.area else "",
                        "device_rack": device.rack.name if device.rack else "",
                        "device_location": device_location,
                        "module": None,
                        "module_name": "",
                        "module_serial": "",
                        "module_description": "",
                    }
                )
            continue

        for module in modules:
            module_match = module_matches(module)
            if device_match or module_match or not query:
                rows.append(
                    {
                        "device": device,
                        "device_name": device.name or "",
                        "device_serial": device.serial_number or "",
                        "device_site_id": str(device.site.id) if device.site else "",
                        "device_site": device.site.name if device.site else "",
                        "device_area": device.area.name if device.area else "",
                        "device_rack": device.rack.name if device.rack else "",
                        "device_location": device_location,
                        "module": module,
                        "module_name": module.name or "",
                        "module_serial": module.serial_number or "",
                        "module_description": module.description or "",
                    }
                )

    return rows


def _sort_inventory_rows(rows, sort_field):
    reverse = False
    field = sort_field or "device_name"
    if field.startswith("-"):
        reverse = True
        field = field[1:]
    sort_keys = {
        "device_name": lambda row: _natural_sort_key(row["device_name"]),
        "device_serial": lambda row: str(row["device_serial"]).lower(),
        "device_site": lambda row: _natural_sort_key(row["device_site"]),
        "device_area": lambda row: _natural_sort_key(row["device_area"]),
        "device_rack": lambda row: _natural_sort_key(row["device_rack"]),
        "device_location": lambda row: _natural_sort_key(row["device_location"]),
        "module_name": lambda row: _natural_sort_key(row["module_name"]),
        "module_serial": lambda row: str(row["module_serial"]).lower(),
        "module_description": lambda row: str(row["module_description"]).lower(),
    }
    sort_key = sort_keys.get(field, sort_keys["device_name"])
    rows.sort(key=sort_key, reverse=reverse)
    return rows

# -----------------------
# HTML Views
# -----------------------
class DeviceListView(LoginRequiredMixin, ListView):
    model = Device
    template_name = "dcim/templates/dcim/device_list.html"
    context_object_name = "devices"
    paginate_by = 50
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
            "device_type",
            "device_type__vendor",
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

        interface_status = self.request.GET.get("interface_status", "").strip()
        valid_interface_statuses = {choice[0] for choice in InterfaceStatusChoices.CHOICES}
        if interface_status in valid_interface_statuses:
            self.current_interface_status = interface_status
            queryset = queryset.filter(interfaces__status=interface_status).distinct()
        else:
            self.current_interface_status = ""

        self.tag_choices = list(Tag.objects.all().order_by("name"))
        tag = self.request.GET.get("tag", "").strip()
        tag_ids = {str(tag_obj.id) for tag_obj in self.tag_choices}
        if tag and tag in tag_ids:
            self.current_tag_filter = tag
            queryset = queryset.filter(tags__id=tag)
        else:
            self.current_tag_filter = ""

        search = self.request.GET.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(management_ip__icontains=search)
                | Q(serial_number__icontains=search)
                | Q(image_version__icontains=search)
                | Q(device_type__model__icontains=search)
                | Q(device_type__vendor__name__icontains=search)
                | Q(area__name__icontains=search)
                | Q(rack__name__icontains=search)
                | Q(site__name__icontains=search)
                | Q(site__organization__name__icontains=search)
            ).distinct()

        sort = self.request.GET.get("sort", "name").strip()
        sort_field = sort.lstrip("-")
        sortable_fields = {
            "name",
            "management_ip",
            "status",
            "device_type__model",
            "serial_number",
            "area__name",
            "rack__name",
            "site__name",
            "image_version",
            "reachability",
        }
        if sort_field in sortable_fields:
            if sort_field == "reachability":
                queryset = queryset.annotate(
                    reachability_score=Case(
                        When(runtime__reachable_ping=True, then=Value(1)),
                        When(runtime__reachable_ssh=True, then=Value(1)),
                        When(runtime__reachable_snmp=True, then=Value(1)),
                        When(runtime__reachable_netconf=True, then=Value(1)),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                )
                direction = "-" if sort.startswith("-") else ""
                queryset = queryset.order_by(f"{direction}reachability_score", "name")
            else:
                queryset = queryset.order_by(sort)

        return queryset


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['sort_field'] = self.request.GET.get('sort', 'name')
        context['paginate_by'] = getattr(self, "current_paginate_by", self.paginate_by)
        context['site_choices'] = self.site_filter_choices
        context['site_filter'] = getattr(self, "current_site_filter", "all")
        context['tag_choices'] = self.tag_choices
        context['tag_filter'] = getattr(self, "current_tag_filter", "")
        context['per_page_options'] = self.per_page_options
        context['interface_status_filter'] = getattr(self, "current_interface_status", "")
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

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get("tag_action")
        if action == "add":
            tag_id = request.POST.get("tag_id")
            if tag_id:
                try:
                    tag = Tag.objects.get(id=tag_id)
                    self.object.tags.add(tag)
                    messages.success(request, f"Tag '{tag.name}' added.")
                except Tag.DoesNotExist:
                    messages.error(request, "Tag not found.")
        elif action == "remove":
            tag_id = request.POST.get("tag_id")
            if tag_id:
                try:
                    tag = Tag.objects.get(id=tag_id)
                    if tag.name in ("reachability_check", "config_backup"):
                        messages.error(
                            request,
                            "This tag can only be removed by an administrator.",
                        )
                    else:
                        self.object.tags.remove(tag)
                        messages.success(request, f"Tag '{tag.name}' removed.")
                except Tag.DoesNotExist:
                    messages.error(request, "Tag not found.")
        return redirect(request.path)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        device = self.get_object()

        interfaces = sorted(
            device.interfaces.all(),
            key=lambda iface: _natural_sort_key(iface.name),
        )
        modules = sorted(
            device.modules.all(),
            key=lambda module: _natural_sort_key(module.name),
        )

        context["preview_limit"] = PREVIEW_LIMIT
        context["interfaces_count"] = len(interfaces)
        context["interfaces_preview"] = interfaces[:PREVIEW_LIMIT]
        context["modules_count"] = len(modules)
        context["modules_preview"] = modules[:PREVIEW_LIMIT]
        context["reachability_checks"] = get_reachability_checks(get_system_settings())
        latest_config = (
            DeviceConfiguration.objects.filter(device=device)
            .order_by("-collected_at")
            .first()
        )
        if latest_config:
            preview_lines = (latest_config.config_text or "").splitlines()
            context["latest_config"] = latest_config
            context["latest_config_preview"] = "\n".join(preview_lines[:20])
        else:
            context["latest_config"] = None
            context["latest_config_preview"] = ""
        context["available_tags"] = Tag.objects.all().order_by("name")
        context["stack_members"] = device.stack_members.order_by("switch_number")
        context["neighbors"] = (
            device.topology_neighbors.select_related("local_interface", "neighbor_device")
            .order_by("protocol", "local_interface__name", "neighbor_name", "-last_seen")
        )
        return context


@login_required
def device_modules(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    search_query = request.GET.get("search", "").strip()
    sort_field = request.GET.get("sort", "name")

    modules = device.modules.all()
    if search_query:
        modules = modules.filter(
            Q(name__icontains=search_query)
            | Q(serial_number__icontains=search_query)
            | Q(description__icontains=search_query)
        )

    allowed_sort_fields = {"name", "serial_number", "description"}
    if sort_field not in allowed_sort_fields:
        sort_field = "name"

    if sort_field == "name":
        modules_list = sorted(
            modules,
            key=lambda module: _natural_sort_key(module.name),
        )
    else:
        modules_list = list(modules.order_by(sort_field))

    paginate_by = _get_paginate_by(request, default=50)
    paginator = Paginator(modules_list, paginate_by)
    page_number = request.GET.get("page")
    modules_page = paginator.get_page(page_number)

    context = {
        "device": device,
        "modules": modules_page,
        "search_query": search_query,
        "sort_field": sort_field,
        "paginate_by": paginate_by,
        "per_page_options": PER_PAGE_OPTIONS,
    }
    return render(request, "dcim/module_list.html", context)


@login_required
def device_interfaces(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    search_query = request.GET.get("search", "").strip()
    sort_field = request.GET.get("sort", "name")

    interfaces = device.interfaces.all()
    if search_query:
        interfaces = interfaces.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(ip_address__icontains=search_query)
            | Q(vlan_raw__icontains=search_query)
            | Q(status__icontains=search_query)
            | Q(duplex__icontains=search_query)
            | Q(speed_mode__icontains=search_query)
        )

    allowed_sort_fields = {
        "name",
        "description",
        "status",
        "ip_address",
        "speed",
        "duplex",
        "speed_mode",
    }
    if sort_field not in allowed_sort_fields:
        sort_field = "name"

    if sort_field == "name":
        interfaces_list = sorted(
            interfaces,
            key=lambda iface: _natural_sort_key(iface.name),
        )
    else:
        interfaces_list = list(interfaces.order_by(sort_field))

    paginate_by = _get_paginate_by(request, default=50)
    paginator = Paginator(interfaces_list, paginate_by)
    page_number = request.GET.get("page")
    interfaces_page = paginator.get_page(page_number)

    context = {
        "device": device,
        "interfaces": interfaces_page,
        "search_query": search_query,
        "sort_field": sort_field,
        "paginate_by": paginate_by,
        "per_page_options": PER_PAGE_OPTIONS,
    }
    return render(request, "dcim/interface_list.html", context)


@login_required
def err_disabled_interfaces(request):
    search_query = request.GET.get("search", "").strip()
    sort_field = request.GET.get("sort", "device__name").strip()

    site_choices = [("all", "All Sites")]
    for site in Site.objects.order_by("name"):
        site_choices.append((str(site.id), site.name))
    site_filter = request.GET.get("site", "all")
    valid_site_keys = {choice[0] for choice in site_choices}
    if site_filter not in valid_site_keys:
        site_filter = "all"

    interfaces = Interface.objects.select_related(
        "device",
        "device__site",
    ).filter(status=InterfaceStatusChoices.ERR_DISABLED)

    if site_filter != "all":
        interfaces = interfaces.filter(device__site_id=site_filter)

    tag_choices = list(Tag.objects.all().order_by("name"))
    tag_filter = request.GET.get("tag", "").strip()
    tag_ids = {str(tag.id) for tag in tag_choices}
    if tag_filter and tag_filter in tag_ids:
        interfaces = interfaces.filter(device__tags__id=tag_filter).distinct()
    else:
        tag_filter = ""

    if search_query:
        interfaces = interfaces.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(ip_address__icontains=search_query)
            | Q(vlan_raw__icontains=search_query)
            | Q(device__name__icontains=search_query)
            | Q(device__management_ip__icontains=search_query)
            | Q(device__site__name__icontains=search_query)
        )

    allowed_sort_fields = {
        "device__name",
        "device__management_ip",
        "name",
        "description",
        "ip_address",
        "speed",
        "status",
        "device__site__name",
    }
    if sort_field.lstrip("-") not in allowed_sort_fields:
        sort_field = "device__name"

    interfaces = interfaces.order_by(sort_field)

    paginate_by = _get_paginate_by(request, default=50)
    paginator = Paginator(interfaces, paginate_by)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "interfaces": page_obj,
        "search_query": search_query,
        "sort_field": sort_field,
        "paginate_by": paginate_by,
        "per_page_options": PER_PAGE_OPTIONS,
        "site_choices": site_choices,
        "site_filter": site_filter,
        "tag_choices": tag_choices,
        "tag_filter": tag_filter,
    }
    return render(request, "dcim/err_disabled_interfaces.html", context)


@login_required
def all_interfaces(request):
    search_query = request.GET.get("search", "").strip()
    sort_field = request.GET.get("sort", "device__name").strip()

    site_choices = [("all", "All Sites")]
    for site in Site.objects.order_by("name"):
        site_choices.append((str(site.id), site.name))
    site_filter = request.GET.get("site", "all")
    valid_site_keys = {choice[0] for choice in site_choices}
    if site_filter not in valid_site_keys:
        site_filter = "all"

    interfaces = Interface.objects.select_related(
        "device",
        "device__site",
    )

    if site_filter != "all":
        interfaces = interfaces.filter(device__site_id=site_filter)

    tag_choices = list(Tag.objects.all().order_by("name"))
    tag_filter = request.GET.get("tag", "").strip()
    tag_ids = {str(tag.id) for tag in tag_choices}
    if tag_filter and tag_filter in tag_ids:
        interfaces = interfaces.filter(device__tags__id=tag_filter).distinct()
    else:
        tag_filter = ""

    if search_query:
        interfaces = interfaces.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(ip_address__icontains=search_query)
            | Q(vlan_raw__icontains=search_query)
            | Q(status__icontains=search_query)
            | Q(device__name__icontains=search_query)
            | Q(device__management_ip__icontains=search_query)
            | Q(device__site__name__icontains=search_query)
        )

    allowed_sort_fields = {
        "device__name",
        "device__management_ip",
        "name",
        "description",
        "ip_address",
        "status",
        "device__site__name",
    }
    if sort_field.lstrip("-") not in allowed_sort_fields:
        sort_field = "device__name"

    interfaces = interfaces.order_by(sort_field)

    paginate_by = _get_paginate_by(request, default=50)
    paginator = Paginator(interfaces, paginate_by)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "interfaces": page_obj,
        "search_query": search_query,
        "sort_field": sort_field,
        "paginate_by": paginate_by,
        "per_page_options": PER_PAGE_OPTIONS,
        "site_choices": site_choices,
        "site_filter": site_filter,
        "tag_choices": tag_choices,
        "tag_filter": tag_filter,
    }
    return render(request, "dcim/all_interfaces.html", context)


@login_required
def inventory_list(request):
    search_query = request.GET.get("search", "").strip()
    sort_field = request.GET.get("sort", "device_name")

    site_choices = [("all", "All Sites")]
    for site in Site.objects.order_by("name"):
        site_choices.append((str(site.id), site.name))
    site_filter = request.GET.get("site", "all")
    valid_site_keys = {choice[0] for choice in site_choices}
    if site_filter not in valid_site_keys:
        site_filter = "all"

    rows = _build_inventory_rows(search_query)
    if site_filter != "all":
        rows = [row for row in rows if row.get("device_site_id") == site_filter]
    tag_choices = list(Tag.objects.all().order_by("name"))
    tag_filter = request.GET.get("tag", "").strip()
    tag_ids = {str(tag.id) for tag in tag_choices}
    if tag_filter and tag_filter in tag_ids:
        rows = [
            row
            for row in rows
            if any(str(tag.id) == tag_filter for tag in row["device"].tags.all())
        ]
    else:
        tag_filter = ""
    rows = _sort_inventory_rows(rows, sort_field)

    paginate_by = _get_paginate_by(request, default=50)
    paginator = Paginator(rows, paginate_by)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "rows": page_obj,
        "search_query": search_query,
        "sort_field": sort_field,
        "paginate_by": paginate_by,
        "per_page_options": PER_PAGE_OPTIONS,
        "site_choices": site_choices,
        "site_filter": site_filter,
        "tag_choices": tag_choices,
        "tag_filter": tag_filter,
    }
    return render(request, "dcim/inventory.html", context)


@login_required
def inventory_export(request):
    search_query = request.GET.get("search", "").strip()
    sort_field = request.GET.get("sort", "device_name")
    site_filter = request.GET.get("site", "all")
    tag_filter = request.GET.get("tag", "").strip()
    tag_ids = set(
        Tag.objects.filter(id=tag_filter).values_list("id", flat=True)
    )

    rows = _build_inventory_rows(search_query)
    if site_filter != "all":
        rows = [row for row in rows if row.get("device_site_id") == site_filter]
    if tag_filter and str(tag_filter) in {str(tag_id) for tag_id in tag_ids}:
        rows = [
            row
            for row in rows
            if any(str(tag.id) == tag_filter for tag in row["device"].tags.all())
        ]
    rows = _sort_inventory_rows(rows, sort_field)

    wb = Workbook()
    ws = wb.active
    ws.title = "Inventory"
    headers = [
        "Device",
        "Device Serial",
        "Location",
        "Inventory Number",
        "Module",
        "Module Serial",
        "Description",
    ]
    ws.append(headers)

    for row in rows:
        device = row["device"]
        module = row["module"]
        module_serial = ""
        if module:
            module_serial = module.serial_number_display or ""
        ws.append(
            [
                row["device_name"],
                row["device_serial"],
                row.get("device_location") or "",
                device.inventory_number or "",
                row["module_name"],
                module_serial,
                row["module_description"],
            ]
        )

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="inventory.xlsx"'
    wb.save(response)
    return response


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
    queryset = DeviceConfiguration.objects.filter(device=device).order_by("-collected_at")
    configurations = list(queryset)
    config_rows = []
    for idx, config in enumerate(configurations):
        previous = configurations[idx + 1] if idx + 1 < len(configurations) else None
        config_rows.append({"config": config, "previous": previous})
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
        messages.error(request, "Select two configurations to compare.")

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
