from collections import defaultdict
from typing import List

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from core.forms.organization_forms import (
    OrganizationForm,
    SiteForm,
    AreaForm,
    RackForm,
)
from dcim.models import Organization, Site, Area, Rack, Device


def _build_area_tree(areas, selected_area_id=None):
    """Return a nested tree structure from a flat area queryset."""
    children = defaultdict(list)
    area_map = {}
    roots: List[Area] = []

    for area in areas:
        area_map[area.id] = area
        children[area.parent_id].append(area)

    for area in areas:
        if area.parent_id is None:
            roots.append(area)

    def build(node):
        child_nodes = [build(child) for child in sorted(children[node.id], key=lambda a: a.name)]
        is_open = node.id == selected_area_id or any(c["open"] for c in child_nodes)
        return {
            "area": node,
            "children": child_nodes,
            "open": is_open,
        }

    return [build(root) for root in sorted(roots, key=lambda a: a.name)]


def _render_site_detail(request, site, selected_area_id=None, error=None):
    areas = (
        site.areas.select_related("parent")
        .prefetch_related("children")
        .order_by("name")
    )

    selected_area = None
    selected_area_id = selected_area_id or request.GET.get("area")
    if selected_area_id:
        selected_area = areas.filter(id=selected_area_id).first()
    if selected_area is None:
        selected_area = areas.first()

    area_tree = _build_area_tree(areas, selected_area.id if selected_area else None)
    rack_edit_id = request.GET.get("rack")
    rack_edit = None
    if rack_edit_id:
        try:
            rack_edit = Rack.objects.get(id=rack_edit_id, area__site=site)
        except Rack.DoesNotExist:
            rack_edit = None

    racks = Rack.objects.filter(area=selected_area).order_by("name") if selected_area else []

    context = {
        "site": site,
        "area_tree": area_tree,
        "selected_area": selected_area,
        "areas_exist": areas.exists(),
        "area_form": AreaForm(instance=selected_area) if selected_area else AreaForm(),
        "child_area_form": AreaForm(),
        "rack_form": RackForm(),
        "racks": racks,
        "rack_edit": rack_edit,
        "error": error,
        "oob": False,
    }
    return render(request, "core/organization/_site_detail.html", context)


def _render_site_list(request, organization, selected_site=None, include_detail=False):
    sites = organization.sites.order_by("name") if organization else Site.objects.none()
    site_list_html = render_to_string(
        "core/organization/_site_list.html",
        {"sites": sites, "selected_site": selected_site, "organization": organization},
        request=request,
    )

    if include_detail and selected_site:
        detail_html = render_to_string(
            "core/organization/_site_detail.html",
            {
                **_site_detail_context(request, selected_site),
                "oob": True,
            },
            request=request,
        )
        return HttpResponse(site_list_html + detail_html)

    return HttpResponse(site_list_html)


def _site_detail_context(request, site):
    areas = (
        site.areas.select_related("parent")
        .prefetch_related("children")
        .order_by("name")
    )
    selected_area_id = request.GET.get("area")
    selected_area = None
    if selected_area_id:
        selected_area = areas.filter(id=selected_area_id).first()
    if selected_area is None:
        selected_area = areas.first()

    area_tree = _build_area_tree(areas, selected_area.id if selected_area else None)
    rack_edit_id = request.GET.get("rack")
    rack_edit = None
    if rack_edit_id:
        try:
            rack_edit = Rack.objects.get(id=rack_edit_id, area__site=site)
        except Rack.DoesNotExist:
            rack_edit = None
    racks = Rack.objects.filter(area=selected_area).order_by("name") if selected_area else []

    return {
        "site": site,
        "area_tree": area_tree,
        "selected_area": selected_area,
        "areas_exist": areas.exists(),
        "area_form": AreaForm(instance=selected_area) if selected_area else AreaForm(),
        "child_area_form": AreaForm(),
        "rack_form": RackForm(),
        "racks": racks,
        "rack_edit": rack_edit,
        "error": None,
    }


@method_decorator(login_required, name="dispatch")
class OrganizationHomeView(TemplateView):
    template_name = "core/organization/index.html"

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if request.headers.get("HX-Request"):
            return render(request, "core/organization/_page.html", context)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = Organization.objects.order_by("name").first()
        selected_site_id = self.request.GET.get("site")
        sites = organization.sites.order_by("name") if organization else Site.objects.none()
        selected_site = None
        if selected_site_id:
            selected_site = sites.filter(id=selected_site_id).first()
        if selected_site is None:
            selected_site = sites.first()

        context.update(
            {
                "organization": organization,
                "organization_form": OrganizationForm(instance=organization),
                "sites": sites,
                "selected_site": selected_site,
                **(_site_detail_context(self.request, selected_site) if selected_site else {}),
            }
        )
        return context


@method_decorator(login_required, name="dispatch")
class RackDetailView(TemplateView):
    """Read-only rack visualization for audits/planning."""

    template_name = "core/organization/rack_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rack_id = kwargs.get("rack_id")
        rack = get_object_or_404(
            Rack.objects.select_related("area__site", "rack_type").prefetch_related(
                "devices__device_type", "devices__role"
            ),
            id=rack_id,
        )
        show_devices = self.request.user.has_perm("dcim.view_device")

        devices = list(rack.devices.all().order_by("position", "name"))

        layout = self._build_layout(rack, devices) if show_devices else []
        rack_power_watts = 0
        rack_weight_kg = 0
        for d in devices:
            dt = d.device_type
            if not dt:
                continue
            stack_factor = max(1, d.stack_members.count() if d.is_stacked else 1)
            rack_power_watts += (dt.default_ac_power_supply_watts or 0) * stack_factor
            rack_weight_kg += float(dt.weight or 0) * stack_factor

        context.update(
            {
                "rack": rack,
                "show_devices": show_devices,
                "layout": layout,
                "device_list": devices,
                "has_positions": bool(layout),
                "rack_power_watts": rack_power_watts,
                "rack_weight_kg": rack_weight_kg,
            }
        )
        return context

    def _build_layout(self, rack, devices):
        """Return rack units from top to bottom with device occupancy."""
        if not rack.u_height or not devices:
            return []

        occupancy = {}
        for device in devices:
            if device.position is None or not device.device_type:
                continue
            try:
                start = int(device.position)  # lowest-numbered unit occupied
                base_height = int(device.device_type.u_height or 1)
                stack_factor = max(1, device.stack_members.count() if device.is_stacked else 1)
                height = base_height * stack_factor
            except (TypeError, ValueError):
                continue
            if start < 1 or start > int(rack.u_height):
                continue  # outside rack bounds

            head = min(int(rack.u_height), start + height - 1)
            effective_height = head - start + 1

            # Mark all occupied units with a pointer to the head index
            for unit in range(start, head + 1):
                occupancy[unit] = {
                    "device": device,
                    "start": start,
                    "height": effective_height,
                    "head": head,
                    "stack_count": stack_factor,
                }

        units = []
        for unit in range(int(rack.u_height), 0, -1):
            block = occupancy.get(unit)
            is_head = block and block.get("head") == unit
            units.append(
                {
                    "unit": unit,
                    "device": block["device"] if is_head else None,
                    "height": block["height"] if is_head else None,
                    "render_height_px": (block["height"] * 36) if is_head else None,
                    "stack_count": block["stack_count"] if is_head else None,
                    "stack_range": range(1, block["stack_count"] + 1) if is_head and block.get("stack_count") else None,
                    "occupied": bool(block),
                }
            )
        return units


@login_required
def organization_update(request, org_id):
    organization = get_object_or_404(Organization, id=org_id)
    form = OrganizationForm(request.POST, instance=organization)
    if form.is_valid():
        form.save()
        response = HttpResponse(status=204)
        response["HX-Redirect"] = reverse("organization_home")
        return response

    html = render_to_string(
        "core/organization/_organization_card.html",
        {"organization": organization, "organization_form": form},
        request=request,
    )
    return HttpResponse(html, status=400)


@login_required
def site_detail(request, site_id):
    site = get_object_or_404(Site, id=site_id)
    return _render_site_detail(request, site, request.GET.get("area"))


@login_required
def site_create(request):
    organization = Organization.objects.order_by("name").first()
    if not organization:
        return HttpResponseBadRequest("Organization is required.")

    form = SiteForm(request.POST)
    if form.is_valid():
        site = form.save(commit=False)
        site.organization = organization
        site.save()
        response = HttpResponse(status=204)
        response["HX-Redirect"] = reverse("organization_home") + f"?site={site.id}"
        return response

    sites = organization.sites.order_by("name")
    html = render_to_string(
        "core/organization/_site_list.html",
        {"sites": sites, "selected_site": None, "organization": organization, "site_form": form},
        request=request,
    )
    return HttpResponse(html, status=400)


@login_required
def site_edit_form(request, site_id):
    site = get_object_or_404(Site, id=site_id)
    form = SiteForm(instance=site)
    html = render_to_string(
        "core/organization/_site_row_form.html",
        {"form": form, "site": site},
        request=request,
    )
    return HttpResponse(html)


@login_required
def site_update(request, site_id):
    site = get_object_or_404(Site, id=site_id)
    form = SiteForm(request.POST, instance=site)
    if form.is_valid():
        form.save()
        response = HttpResponse(status=204)
        response["HX-Redirect"] = reverse("organization_home") + f"?site={site.id}"
        return response

    html = render_to_string(
        "core/organization/_site_row_form.html",
        {"form": form, "site": site},
        request=request,
    )
    return HttpResponse(html, status=400)


@login_required
def site_delete(request, site_id):
    site = get_object_or_404(Site, id=site_id)
    site.delete()
    response = HttpResponse(status=204)
    response["HX-Redirect"] = reverse("organization_home")
    return response


@login_required
def area_create(request):
    site_id = request.POST.get("site_id")
    site = get_object_or_404(Site, id=site_id)
    parent_id = request.POST.get("parent_id")
    parent = None
    if parent_id:
        parent = get_object_or_404(Area, id=parent_id, site=site)

    form = AreaForm(request.POST)
    if form.is_valid():
        area = form.save(commit=False)
        area.site = site
        area.parent = parent
        area.save()
        return _render_site_detail(request, site, selected_area_id=area.id)

    return _render_site_detail(request, site, selected_area_id=parent.id if parent else None, error="Invalid area data.")


@login_required
def area_update(request, area_id):
    area = get_object_or_404(Area, id=area_id)
    site = area.site
    form = AreaForm(request.POST, instance=area)
    if form.is_valid():
        form.save()
        return _render_site_detail(request, site, selected_area_id=area.id)
    return _render_site_detail(request, site, selected_area_id=area.id, error="Unable to update area.")


@login_required
def area_delete(request, area_id):
    area = get_object_or_404(Area, id=area_id)
    site = area.site
    if area.children.exists():
        return _render_site_detail(request, site, selected_area_id=area.id, error="Cannot delete an area that has child areas.")

    area.delete()
    return _render_site_detail(request, site)


@login_required
def rack_create(request):
    area_id = request.POST.get("area_id")
    area = get_object_or_404(Area, id=area_id)
    site = area.site
    form = RackForm(request.POST)
    if form.is_valid():
        rack = form.save(commit=False)
        rack.area = area
        rack.save()
        return _render_site_detail(request, site, selected_area_id=area.id)
    return _render_site_detail(request, site, selected_area_id=area.id, error="Unable to create rack.")


@login_required
def rack_update(request, rack_id):
    rack = get_object_or_404(Rack, id=rack_id)
    area = rack.area
    site = area.site
    form = RackForm(request.POST, instance=rack)
    if form.is_valid():
        form.save()
        return _render_site_detail(request, site, selected_area_id=area.id)
    return _render_site_detail(request, site, selected_area_id=area.id, error="Unable to update rack.")


@login_required
def rack_delete(request, rack_id):
    rack = get_object_or_404(Rack, id=rack_id)
    area = rack.area
    site = area.site
    rack.delete()
    return _render_site_detail(request, site, selected_area_id=area.id)
