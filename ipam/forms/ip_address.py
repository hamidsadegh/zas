from django import forms
import ipaddress

from dcim.models import Interface
from ipam.models import IPAddress, Prefix
from ipam.services.ip_allocation_service import IPAllocationService


class IPAddressAssignForm(forms.ModelForm):
    class Meta:
        model = IPAddress
        fields = ["interface", "prefix", "address", "status", "role", "hostname"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["interface"].queryset = Interface.objects.all().order_by("device__name", "name")
        self.fields["prefix"].queryset = Prefix.objects.select_related("vrf", "site").order_by("cidr")
        self.fields["address"].required = False

    def clean(self):
        cleaned = super().clean()
        prefix = cleaned.get("prefix")
        address = cleaned.get("address")
        interface = cleaned.get("interface")

        if not prefix:
            return cleaned

        if not address:
            try:
                cleaned["address"] = IPAllocationService.next_available_ip(prefix)
                address = cleaned["address"]
            except RuntimeError as exc:
                self.add_error("address", str(exc))
                return cleaned

        try:
            ip_obj = ipaddress.ip_address(address)
        except ValueError:
            self.add_error("address", "Enter a valid IP address.")
            return cleaned

        network = ipaddress.ip_network(prefix.cidr, strict=False)
        if ip_obj not in network:
            self.add_error("address", "IP must belong to the selected prefix.")

        # Duplicate within VRF (using prefix.vrf)
        vrf = prefix.vrf_id
        exists = IPAddress.objects.filter(address=address, prefix__vrf_id=vrf)
        if self.instance.pk:
            exists = exists.exclude(pk=self.instance.pk)
        if exists.exists():
            self.add_error("address", "IP address already exists in this VRF.")

        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if commit:
            obj.save()
            self.save_m2m()
        return obj
