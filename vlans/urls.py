from django.urls import path

from .views import (
    VLANListView,
    VLANCreateView,
    VLANUpdateView,
    VLANDeleteView,
    VLANExportView,
)

urlpatterns = [
    path("", VLANListView.as_view(), name="vlan_list"),
    path("add/", VLANCreateView.as_view(), name="vlan_add"),
    path("<int:pk>/edit/", VLANUpdateView.as_view(), name="vlan_edit"),
    path("<int:pk>/delete/", VLANDeleteView.as_view(), name="vlan_delete"),
    path("export/", VLANExportView.as_view(), name="vlan_export"),
]
