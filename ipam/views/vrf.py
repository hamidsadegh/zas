from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from ipam.forms.vrf import VRFForm
from ipam.models import VRF, Prefix


class VRFListView(LoginRequiredMixin, ListView):
    model = VRF
    template_name = "ipam/vrf_list.html"
    context_object_name = "vrfs"
    queryset = VRF.objects.select_related("site").order_by("site__name", "name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = VRFForm()
        return ctx


class VRFDetailView(LoginRequiredMixin, DetailView):
    model = VRF
    template_name = "ipam/vrf_detail.html"
    context_object_name = "vrf"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["prefixes"] = Prefix.objects.filter(vrf=self.object).order_by("cidr")
        return ctx


class VRFCreateView(LoginRequiredMixin, CreateView):
    model = VRF
    form_class = VRFForm
    template_name = "ipam/vrf_form.html"
    success_url = reverse_lazy("ipam:vrf_list")


class VRFUpdateView(LoginRequiredMixin, UpdateView):
    model = VRF
    form_class = VRFForm
    template_name = "ipam/vrf_form.html"
    success_url = reverse_lazy("ipam:vrf_list")


class VRFDeleteView(LoginRequiredMixin, DeleteView):
    model = VRF
    template_name = "ipam/vrf_confirm_delete.html"
    success_url = reverse_lazy("ipam:vrf_list")
