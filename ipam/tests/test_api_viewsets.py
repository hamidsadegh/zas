import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from api.v1.ipam.serializers import IPAddressSerializer, PrefixSerializer
from dcim.models import Area, Device, DeviceRole, DeviceType, Interface, Organization, Site, Vendor
from ipam.models import IPAddress, Prefix, VRF


@pytest.fixture
def api_client():
    user = get_user_model().objects.create_user(username="ipam-api", password="pass")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _inventory(name: str):
    organization = Organization.objects.create(name=f"{name}-org")
    site = Site.objects.create(name=f"{name}-site", organization=organization)
    area = Area.objects.create(name=f"{name}-area", site=site)
    vendor = Vendor.objects.create(name=f"{name}-vendor")
    device_type = DeviceType.objects.create(vendor=vendor, model=f"{name}-model")
    role = DeviceRole.objects.create(name=f"{name}-role")
    device = Device.objects.create(
        name=f"{name}-device",
        management_ip=f"192.0.2.{len(name) + 10}",
        site=site,
        area=area,
        device_type=device_type,
        role=role,
        status="active",
    )
    interface = Interface.objects.create(name="Gi1/0/1", device=device)
    return site, interface


@pytest.mark.django_db
def test_prefix_list_filters_by_length(api_client):
    site, _ = _inventory("prefix")
    vrf = VRF.objects.create(name="blue", site=site)
    wanted = Prefix.objects.create(cidr="10.0.0.0/24", site=site, vrf=vrf)
    Prefix.objects.create(cidr="10.0.0.0/25", site=site, vrf=vrf)

    response = api_client.get("/api/v1/ipam/prefixes/?length=24")

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload] == [str(wanted.id)]


@pytest.mark.django_db
def test_ipaddress_list_filters_by_vrf(api_client):
    site, interface = _inventory("vrf")
    vrf_a = VRF.objects.create(name="blue", site=site)
    vrf_b = VRF.objects.create(name="green", site=site)
    prefix_a = Prefix.objects.create(cidr="10.0.0.0/24", site=site, vrf=vrf_a)
    prefix_b = Prefix.objects.create(cidr="10.0.1.0/24", site=site, vrf=vrf_b)
    wanted = IPAddress.objects.create(address="10.0.0.10", prefix=prefix_a, interface=interface)
    IPAddress.objects.create(address="10.0.1.10", prefix=prefix_b, interface=interface)

    response = api_client.get(f"/api/v1/ipam/ip-addresses/?vrf={vrf_a.id}")

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload] == [str(wanted.id)]


@pytest.mark.django_db
def test_prefix_serializer_normalizes_cidr():
    site, _ = _inventory("serializer")
    serializer = PrefixSerializer(
        data={
            "cidr": "10.0.2.1/24",
            "site": str(site.id),
            "status": "active",
            "role": "user",
        }
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["cidr"] == "10.0.2.0/24"


@pytest.mark.django_db
def test_ipaddress_serializer_rejects_ip_outside_prefix():
    site, interface = _inventory("outside")
    prefix = Prefix.objects.create(cidr="10.0.3.0/24", site=site)
    serializer = IPAddressSerializer(
        data={
            "address": "10.0.4.10",
            "prefix": str(prefix.id),
            "interface": str(interface.id),
            "status": "active",
            "role": "secondary",
        }
    )

    assert serializer.is_valid() is False
    assert serializer.errors["address"] == ["IP must belong to the selected prefix."]


@pytest.mark.django_db
def test_ipaddress_serializer_rejects_duplicate_ip_in_same_vrf():
    site, interface = _inventory("duplicate")
    vrf = VRF.objects.create(name="dup-vrf", site=site)
    parent = Prefix.objects.create(cidr="10.0.5.0/24", site=site, vrf=vrf)
    child = Prefix.objects.create(cidr="10.0.5.0/25", site=site, vrf=vrf, parent=parent)
    IPAddress.objects.create(address="10.0.5.10", prefix=parent, interface=interface)
    serializer = IPAddressSerializer(
        data={
            "address": "10.0.5.10",
            "prefix": str(child.id),
            "interface": str(interface.id),
            "status": "active",
            "role": "secondary",
        }
    )

    assert serializer.is_valid() is False
    assert serializer.errors["address"] == ["IP address already exists in this VRF."]
