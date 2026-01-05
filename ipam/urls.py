from django.urls import path

from ipam.views.index import IPAMIndexView
from ipam.views.vrf import (
    VRFListView,
    VRFDetailView,
    VRFCreateView,
    VRFUpdateView,
    VRFDeleteView,
)
from ipam.views.prefix import (
    PrefixListView,
    PrefixDetailView,
    PrefixCreateView,
    PrefixUpdateView,
    PrefixDeleteView,
)
from ipam.views.ip_address import (
    IPAddressListView,
    IPAddressCreateView,
    IPAddressDetailView,
    IPAddressUpdateView,
    IPAddressDeleteView,
)

app_name = "ipam"

urlpatterns = [
    path("", IPAMIndexView.as_view(), name="index"),
    path("vrfs/", VRFListView.as_view(), name="vrf_list"),
    path("vrfs/add/", VRFCreateView.as_view(), name="vrf_add"),
    path("vrfs/<uuid:pk>/", VRFDetailView.as_view(), name="vrf_detail"),
    path("vrfs/<uuid:pk>/edit/", VRFUpdateView.as_view(), name="vrf_edit"),
    path("vrfs/<uuid:pk>/delete/", VRFDeleteView.as_view(), name="vrf_delete"),
    path("prefixes/", PrefixListView.as_view(), name="prefix_list"),
    path("prefixes/add/", PrefixCreateView.as_view(), name="prefix_add"),
    path("prefixes/<uuid:pk>/", PrefixDetailView.as_view(), name="prefix_detail"),
    path("prefixes/<uuid:pk>/edit/", PrefixUpdateView.as_view(), name="prefix_edit"),
    path("prefixes/<uuid:pk>/delete/", PrefixDeleteView.as_view(), name="prefix_delete"),
    path("ip-addresses/", IPAddressListView.as_view(), name="ipaddress_list"),
    path("ip-addresses/add/", IPAddressCreateView.as_view(), name="ipaddress_add"),
    path("ip-addresses/<uuid:pk>/", IPAddressDetailView.as_view(), name="ipaddress_detail"),
    path("ip-addresses/<uuid:pk>/edit/", IPAddressUpdateView.as_view(), name="ipaddress_edit"),
    path("ip-addresses/<uuid:pk>/delete/", IPAddressDeleteView.as_view(), name="ipaddress_delete"),
]
