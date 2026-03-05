from django import forms

from asset.models import InventoryItem
from dcim.models import Area, Site, Vendor


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = [
            "inventory_number",
            "item_type",
            "designation",
            "vendor",
            "model",
            "serial_number",
            "site",
            "area",
            "status",
            "comment",
        ]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["site"].queryset = Site.objects.select_related("organization").order_by(
            "name"
        )
        self.fields["vendor"].queryset = Vendor.objects.order_by("name")
        self.fields["area"].queryset = Area.objects.none()

        site_id = None
        if self.is_bound:
            site_id = self.data.get("site") or None
        elif self.instance.pk and self.instance.site_id:
            site_id = str(self.instance.site_id)
        elif self.initial.get("site"):
            site_id = str(self.initial["site"])

        if site_id:
            self.fields["area"].queryset = Area.objects.filter(site_id=site_id).order_by(
                "name"
            )
