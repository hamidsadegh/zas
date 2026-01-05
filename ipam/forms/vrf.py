from django import forms

from ipam.models import VRF


class VRFForm(forms.ModelForm):
    class Meta:
        model = VRF
        fields = ["name", "site", "rd", "description"]
