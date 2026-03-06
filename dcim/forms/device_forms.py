from django import forms

from asset.models import InventoryItem
from dcim.models import Area, Rack, Vendor


class DeviceDecommissionItemForm(forms.Form):
    class Action:
        STORE = "store"
        DISCARD = "discard"
        CHOICES = (
            (STORE, "Move to storage"),
            (DISCARD, "Discard"),
        )

    source_key = forms.CharField(widget=forms.HiddenInput())
    action = forms.ChoiceField(
        choices=Action.CHOICES,
        initial=Action.STORE,
    )
    item_type = forms.ChoiceField(
        choices=InventoryItem.ItemType.choices,
        required=False,
    )
    designation = forms.ChoiceField(
        choices=InventoryItem.Designation.choices,
        required=False,
    )
    inventory_number = forms.CharField(max_length=100, required=False)
    area = forms.ModelChoiceField(queryset=Area.objects.none(), required=False)
    vendor = forms.ModelChoiceField(queryset=Vendor.objects.none(), required=False)
    status = forms.ChoiceField(
        choices=InventoryItem.Status.choices,
        initial=InventoryItem.Status.IN_STOCK,
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, site=None, **kwargs):
        self.site = site
        super().__init__(*args, **kwargs)
        self.fields["vendor"].queryset = Vendor.objects.order_by("name")
        if site:
            self.fields["area"].queryset = Area.objects.filter(site=site).order_by("name")
        else:
            self.fields["area"].queryset = Area.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get("action")

        designation = (cleaned_data.get("designation") or "").strip()
        inventory_number = (cleaned_data.get("inventory_number") or "").strip()
        comment = (cleaned_data.get("comment") or "").strip()
        cleaned_data["designation"] = designation
        cleaned_data["inventory_number"] = inventory_number
        cleaned_data["comment"] = comment

        if action != self.Action.STORE:
            return cleaned_data

        if not cleaned_data.get("item_type"):
            self.add_error("item_type", "Type is required when moving to storage.")

        if not designation:
            self.add_error("designation", "Designation is required when moving to storage.")

        if (
            cleaned_data.get("status") == InventoryItem.Status.INSTALLED
            and not comment
        ):
            self.add_error(
                "comment",
                "Comment is required when status is set to installed.",
            )

        return cleaned_data


class DeviceReplacementForm(forms.Form):
    name = forms.CharField(max_length=100)
    management_ip = forms.GenericIPAddressField(protocol="IPv4")
    area = forms.ModelChoiceField(queryset=Area.objects.none())
    rack = forms.ModelChoiceField(queryset=Rack.objects.none(), required=False)

    def __init__(self, *args, device=None, **kwargs):
        self.device = device
        super().__init__(*args, **kwargs)

        if device is None:
            self.fields["area"].queryset = Area.objects.none()
            self.fields["rack"].queryset = Rack.objects.none()
            return

        self.fields["area"].queryset = Area.objects.filter(site=device.site).order_by("name")

        area_id = None
        if self.is_bound:
            area_id = self.data.get("area")
        else:
            area_id = (
                self.initial.get("area")
                or getattr(device, "area_id", None)
            )

        if area_id:
            self.fields["rack"].queryset = Rack.objects.filter(area_id=area_id).order_by("name")
        else:
            self.fields["rack"].queryset = Rack.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        area = cleaned_data.get("area")
        rack = cleaned_data.get("rack")
        if area and rack and rack.area_id != area.id:
            self.add_error("rack", "Rack must belong to the selected area.")
        return cleaned_data
