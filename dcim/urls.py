from django.urls import path

from dcim.views.vlan_views import (
    VLANListView,
    VLANAddView,
    VLANUpdateView,
    VLANDeleteView, 
    VLANExportView,
)

from dcim.views.device_views import (
    DeviceListView,
    DeviceDetailView,
    #area_list,
    #area_detail,
    devices_by_area,
    #rack_list,
    racks_by_area,
    device_configuration_history,
    device_configuration_diff,
    device_configuration_visual_diff,
)


urlpatterns = [
    # Devices
    path("devices/", DeviceListView.as_view(), name="device_list"),
    path("devices/<uuid:pk>/", DeviceDetailView.as_view(), name="device_detail"),
    path(
        "devices/<uuid:device_id>/configurations/",
        device_configuration_history,
        name="device_configuration_history",
    ),
    path(
        "devices/<uuid:device_id>/configurations/diff/<uuid:config_id>/<uuid:other_id>/",
        device_configuration_diff,
        name="device_configuration_diff",
    ),
    path(
        "devices/<uuid:device_id>/config/<uuid:config_id>/visual-diff/<uuid:other_id>/",
        device_configuration_visual_diff,
        name="device_configuration_visual_diff",
    ),

    # VLANs
    path("vlans/", VLANListView.as_view(), name="vlan_list"),
    path("vlans/add/", VLANAddView.as_view(), name="vlan_form"),
    path("vlans/<uuid:pk>/edit/", VLANUpdateView.as_view(), name="vlan_edit"),
    path("vlans/<uuid:pk>/delete/", VLANDeleteView.as_view(), name="vlan_delete"),
    path("vlans/export/", VLANExportView.as_view(), name="vlan_export"),

    # Areas
   # path("areas/", area_list, name="area_list"),
  #  path("areas/<uuid:pk>/", area_detail, name="area_detail"),
    path("areas/<uuid:area_id>/devices/", devices_by_area, name="devices_by_area"),

    # Racks
  #  path("racks/", rack_list, name="rack_list"),

    # AJAX endpoint for dynamic rack dropdown
    path("ajax/racks/", racks_by_area, name="racks_by_area"),
]
