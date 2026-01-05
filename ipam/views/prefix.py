from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from ipam.forms.prefix import PrefixForm
from ipam.models import Prefix
from ipam.models import IPAddress


class PrefixListView(LoginRequiredMixin, ListView):
    model = Prefix
    template_name = "ipam/prefix_list.html"
    context_object_name = "prefixes"
    paginate_by = 50

    def get_queryset(self):
        qs = Prefix.objects.select_related("vrf", "site").annotate(ip_count=Count("ip_addresses"))
        vrf = self.request.GET.get("vrf")
        site = self.request.GET.get("site")
        length = self.request.GET.get("length")
        if vrf:
            qs = qs.filter(vrf_id=vrf)
        if site:
            qs = qs.filter(site_id=site)
        if length and length.isdigit():
            qs = qs.filter(cidr__regex=fr"/{length}$")
        return qs.order_by("cidr")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = PrefixForm()
        ctx["prefix_lengths"] = [24, 25, 26, 27, 28, 29, 30, 31, 32]
        return ctx


class PrefixDetailView(LoginRequiredMixin, DetailView):
    model = Prefix
    template_name = "ipam/prefix_detail.html"
    context_object_name = "prefix"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["children"] = self.object.children.order_by("cidr")
        ctx["ip_addresses"] = IPAddress.objects.filter(prefix=self.object).select_related("interface").order_by("address")
        return ctx


class PrefixCreateView(LoginRequiredMixin, CreateView):
    model = Prefix
    form_class = PrefixForm
    template_name = "ipam/prefix_form.html"
    success_url = reverse_lazy("ipam:prefix_list")


class PrefixUpdateView(LoginRequiredMixin, UpdateView):
    model = Prefix
    form_class = PrefixForm
    template_name = "ipam/prefix_form.html"
    success_url = reverse_lazy("ipam:prefix_list")


class PrefixDeleteView(LoginRequiredMixin, DeleteView):
    model = Prefix
    template_name = "ipam/prefix_confirm_delete.html"
    success_url = reverse_lazy("ipam:prefix_list")
