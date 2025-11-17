from django import forms

from .models import VLAN


class VLANForm(forms.ModelForm):
    class Meta:
        model = VLAN
        fields = [
            "site",
            "vlan_id",
            "name",
            "subnet",
            "gateway",
            "usage_area",
            "description",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }
