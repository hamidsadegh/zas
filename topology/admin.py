from django.contrib import admin

from .models import TopologyNeighbor


@admin.register(TopologyNeighbor)
class TopologyNeighborAdmin(admin.ModelAdmin):
    autocomplete_fields = ("device", "local_interface", "neighbor_device")
    list_display = (
        "device",
        "local_interface",
        "neighbor_name",
        "neighbor_device",
        "neighbor_interface",
        "protocol",
        "last_seen",
    )
    list_filter = ("protocol", "device", "neighbor_device")
    list_select_related = ("device", "local_interface", "neighbor_device")
    search_fields = (
        "neighbor_name",
        "neighbor_interface",
        "device__name",
        "local_interface__name",
        "neighbor_device__name",
    )
    ordering = ("-last_seen",)
