from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View

from openpyxl import Workbook

from .forms import VLANForm
from .models import VLAN


class VLANListView(LoginRequiredMixin, ListView):
    model = VLAN
    template_name = "vlans/list.html"
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
        queryset = VLAN.objects.all()
        site = self.request.GET.get("site", "Berlin")
        search = self.request.GET.get("q", "").strip()

        if site in dict(VLAN.SITE_CHOICES):
            queryset = queryset.filter(site=site)

        if search:
            q_objects = Q(
                name__icontains=search
            ) | Q(description__icontains=search) | Q(usage_area__icontains=search) | Q(subnet__icontains=search)
            if search.isdigit():
                q_objects |= Q(vlan_id=int(search))
            queryset = queryset.filter(q_objects)

        sort = self.request.GET.get("sort", "vlan_id")
        allowed = {"vlan_id", "name", "subnet", "usage_area", "site"}
        if sort.lstrip("-") in allowed:
            queryset = queryset.order_by(sort)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["site_filter"] = self.request.GET.get("site", "Berlin")
        context["search_query"] = self.request.GET.get("q", "")
        context["site_choices"] = VLAN.SITE_CHOICES
        context["per_page_options"] = self.per_page_options
        context["paginate_by_value"] = getattr(self, "_current_paginate_by", self.paginate_by)
        return context


class VLANCreateView(LoginRequiredMixin, CreateView):
    model = VLAN
    form_class = VLANForm
    template_name = "vlans/form.html"
    success_url = reverse_lazy("vlan_list")

    def form_valid(self, form):
        messages.success(self.request, "VLAN created successfully.")
        return super().form_valid(form)


class VLANUpdateView(LoginRequiredMixin, UpdateView):
    model = VLAN
    form_class = VLANForm
    template_name = "vlans/form.html"
    success_url = reverse_lazy("vlan_list")

    def form_valid(self, form):
        messages.success(self.request, "VLAN updated successfully.")
        return super().form_valid(form)


class VLANDeleteView(LoginRequiredMixin, DeleteView):
    model = VLAN
    template_name = "vlans/confirm_delete.html"
    success_url = reverse_lazy("vlan_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "VLAN deleted.")
        return super().delete(request, *args, **kwargs)


class VLANExportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        site = request.GET.get("site")
        queryset = VLAN.objects.all()
        if site in dict(VLAN.SITE_CHOICES):
            queryset = queryset.filter(site=site)

        wb = Workbook()
        ws = wb.active
        ws.title = "VLANs"
        headers = ["Site", "VLAN ID", "Name", "Subnet", "Gateway", "Usage Area", "Description"]
        ws.append(headers)

        for vlan in queryset:
            ws.append(
                [
                    vlan.site,
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
