import uuid

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View

from openpyxl import Workbook

from ..forms.vlan_forms import VLANForm
from dcim.models.vlan import VLAN
from dcim.models.site import Site


class VLANListView(LoginRequiredMixin, ListView):
    model = VLAN
    template_name = "dcim/vlan_list.html"
    context_object_name = "vlans"
    paginate_by = 25
    per_page_options = (10, 25, 50, 100)

    def get_paginate_by(self, queryset):
        per_page = self.request.GET.get("paginate_by")
        if per_page and per_page.isdigit() and int(per_page) in self.per_page_options:
            self._current_paginate_by = int(per_page)
            return self._current_paginate_by
        self._current_paginate_by = self.paginate_by
        return self.paginate_by

    def get_queryset(self):
        queryset = VLAN.objects.select_related("site", "site__organization").order_by("vlan_id")

        site = self.request.GET.get("site", "all")
        usage_area = self.request.GET.get("usage_area", "").strip()
        usage_codes = {code for code, _ in VLAN.USAGE_CHOICES}
        try:
            if site != "all":
                uuid.UUID(str(site))
        except (ValueError, TypeError):
            site = "all"
        self._site_filter = site
        self._usage_area_filter = usage_area if usage_area in usage_codes else ""
        search = self.request.GET.get("q", "").strip()

        if site != "all":
            queryset = queryset.filter(site_id=site)

        if self._usage_area_filter:
            queryset = queryset.filter(usage_area=self._usage_area_filter)

        if search:
            q_objects = Q(
                name__icontains=search
            ) | Q(description__icontains=search) | Q(usage_area__icontains=search) | Q(subnet__icontains=search)
            if search.isdigit():
                q_objects |= Q(vlan_id=int(search))
            else:
                q_objects |= Q(site__name__icontains=search)
            queryset = queryset.filter(q_objects)

        sort = self.request.GET.get("sort", "vlan_id")
        allowed = {"vlan_id", "name", "subnet", "usage_area", "site__name"}
        if sort.lstrip("-") in allowed:
            queryset = queryset.order_by(sort)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["site_choices"] = self._site_choices()
        context["site_filter"] = getattr(self, "_site_filter", "all")
        context["usage_area_filter"] = getattr(self, "_usage_area_filter", "")
        context["usage_area_choices"] = [("", "All usage areas")] + list(VLAN.USAGE_CHOICES)
        context["search_query"] = self.request.GET.get("q", "")
        context["per_page_options"] = self.per_page_options
        context["paginate_by_value"] = getattr(self, "_current_paginate_by", self.paginate_by)
        return context

    def _site_choices(self):
        if hasattr(self, "_site_cache"):
            return self._site_cache
        choices = [("all", "All Sites")]
        for site in Site.objects.select_related("organization").order_by("name"):
            label = f"{site.name} ({site.organization.name})"
            choices.append((str(site.id), label))
        self._site_cache = choices
        return choices



class VLANAddView(LoginRequiredMixin, CreateView):
    model = VLAN
    form_class = VLANForm
    template_name = "dcim/vlan_form.html"
    success_url = reverse_lazy("vlan_list")

    def form_valid(self, form):
        messages.success(self.request, "VLAN created successfully.")
        return super().form_valid(form)


class VLANUpdateView(LoginRequiredMixin, UpdateView):
    model = VLAN
    form_class = VLANForm
    template_name = "dcim/vlan_form.html"
    success_url = reverse_lazy("vlan_list")

    def form_valid(self, form):
        messages.success(self.request, "VLAN updated successfully.")
        return super().form_valid(form)


class VLANDeleteView(LoginRequiredMixin, DeleteView):
    model = VLAN
    template_name = "dcim/vlan_confirm_delete.html"
    success_url = reverse_lazy("vlan_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "VLAN deleted.")
        return super().delete(request, *args, **kwargs)


class VLANExportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        site = request.GET.get("site")
        usage_area = request.GET.get("usage_area", "").strip()
        queryset = VLAN.objects.all()
        if site and site != "all":
            try:
                uuid.UUID(str(site))
            except (ValueError, TypeError):
                site = None
            if site:
                queryset = queryset.filter(site_id=site)
        usage_codes = {code for code, _ in VLAN.USAGE_CHOICES}
        if usage_area and usage_area in usage_codes:
            queryset = queryset.filter(usage_area=usage_area)

        wb = Workbook()
        ws = wb.active
        ws.title = "VLANs"
        headers = ["Site", "VLAN ID", "Name", "Subnet", "Gateway", "Usage Area", "Description"]
        ws.append(headers)

        for vlan in queryset:
            ws.append(
                [
                    vlan.site.name if vlan.site else "",
                    vlan.vlan_id,
                    vlan.name,
                    vlan.subnet,
                    vlan.gateway or "",
                    vlan.usage_area,
                    vlan.description or "",
                ]
            )

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="vlans.xlsx"'
        wb.save(response)
        return response
