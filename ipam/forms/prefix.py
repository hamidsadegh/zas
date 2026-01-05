from django import forms

from ipam.models import Prefix


class PrefixForm(forms.ModelForm):
    class Meta:
        model = Prefix
        fields = [
            "cidr",
            "site",
            "vrf",
            "vlan",
            "parent",
            "status",
            "role",
            "description",
        ]
