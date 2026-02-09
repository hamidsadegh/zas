from django import forms

from dcim.models import Organization, Site, Area, Rack


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ["name", "description"]


class SiteForm(forms.ModelForm):
    class Meta:
        model = Site
        fields = ["name", "domain", "description"]


class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = ["name", "description"]


class RackForm(forms.ModelForm):
    class Meta:
        model = Rack
        fields = ["name", "u_height", "description"]
