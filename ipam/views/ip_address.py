from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from django.db.models import Q

from dcim.models import Device, Interface
from ipam.forms.ip_address import IPAddressAssignForm
from ipam.models import IPAddress, Prefix


class IPAddressListView(LoginRequiredMixin, ListView):
    model = IPAddress
    template_name = "ipam/ipaddress_list.html"
    context_object_name = "ip_addresses"
    paginate_by = 50

    def get_queryset(self):
        qs = IPAddress.objects.select_related("prefix", "interface", "interface__device").order_by("address")
        device = self.request.GET.get("device")
        interface = self.request.GET.get("interface")
        prefix = self.request.GET.get("prefix")
        vrf = self.request.GET.get("vrf")
        status = self.request.GET.get("status")

        if device:
            qs = qs.filter(interface__device_id=device)
        if interface:
            qs = qs.filter(interface_id=interface)
        if prefix:
            qs = qs.filter(prefix_id=prefix)
        if vrf:
            qs = qs.filter(prefix__vrf_id=vrf)
        if status:
            qs = qs.filter(status=status)
        search = self.request.GET.get("search", "").strip()
        if search:
            qs = qs.filter(Q(address__icontains=search) | Q(hostname__icontains=search))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["devices"] = Device.objects.all().order_by("name")
        ctx["interfaces"] = Interface.objects.all().order_by("device__name", "name")
        ctx["prefixes"] = Prefix.objects.all().order_by("cidr")
        ctx["form"] = IPAddressAssignForm()
        return ctx


class IPAddressCreateView(LoginRequiredMixin, CreateView):
    model = IPAddress
    form_class = IPAddressAssignForm
    template_name = "ipam/ipaddress_form.html"
    success_url = reverse_lazy("ipam:ipaddress_list")


class IPAddressDetailView(LoginRequiredMixin, DetailView):
    model = IPAddress
    template_name = "ipam/ipaddress_detail.html"
    context_object_name = "ip"


class IPAddressUpdateView(LoginRequiredMixin, UpdateView):
    model = IPAddress
    form_class = IPAddressAssignForm
    template_name = "ipam/ipaddress_form.html"
    success_url = reverse_lazy("ipam:ipaddress_list")


class IPAddressDeleteView(LoginRequiredMixin, DeleteView):
    model = IPAddress
    template_name = "ipam/ipaddress_confirm_delete.html"
    success_url = reverse_lazy("ipam:ipaddress_list")
