from django.contrib import admin

from .models import VLAN


@admin.register(VLAN)
class VLANAdmin(admin.ModelAdmin):
    list_display = ("vlan_id", "name", "site", "subnet", "usage_area")
    list_filter = ("site", "usage_area")
    search_fields = ("vlan_id", "name", "subnet", "description")
