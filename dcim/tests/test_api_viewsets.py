import hashlib
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from rest_framework.test import APIClient

from api.v1.dcim.serializers import AreaSerializer
from dcim.models import (
    Area,
    Device,
    DeviceConfiguration,
    DeviceRole,
    DeviceType,
    Organization,
    Rack,
    Site,
    Vendor,
)


@pytest.fixture
def api_client():
    user = get_user_model().objects.create_user(username="dcim-api", password="pass")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _device_inventory(name: str, ip: str):
    organization = Organization.objects.create(name=f"{name}-org")
    site = Site.objects.create(name=f"{name}-site", organization=organization)
    area = Area.objects.create(name=f"{name}-area", site=site)
    vendor = Vendor.objects.create(name=f"{name}-vendor")
    device_type = DeviceType.objects.create(vendor=vendor, model=f"{name}-model")
    role = DeviceRole.objects.create(name=f"{name}-role")
    device = Device.objects.create(
        name=name,
        management_ip=ip,
        site=site,
        area=area,
        device_type=device_type,
        role=role,
        status="active",
    )
    return site, area, device


def _config(device, text: str, collected_at):
    return DeviceConfiguration.objects.create(
        device=device,
        config_text=text,
        config_hash=hashlib.sha256(text.encode()).hexdigest(),
        collected_at=collected_at,
    )


@pytest.mark.django_db
def test_area_serializer_rejects_parent_from_different_site():
    org = Organization.objects.create(name="Serializer Org")
    site_a = Site.objects.create(name="Site A", organization=org)
    site_b = Site.objects.create(name="Site B", organization=org)
    parent = Area.objects.create(name="Parent", site=site_a)
    serializer = AreaSerializer()

    with pytest.raises(serializers.ValidationError) as excinfo:
        serializer.validate({"site": site_b, "parent": parent, "name": "Child"})

    assert "same site" in str(excinfo.value)


@pytest.mark.django_db
def test_rack_viewset_filters_by_area(api_client):
    org = Organization.objects.create(name="Rack Org")
    site = Site.objects.create(name="Rack Site", organization=org)
    area_a = Area.objects.create(name="Area A", site=site)
    area_b = Area.objects.create(name="Area B", site=site)
    rack_a = Rack.objects.create(name="Rack A", area=area_a)
    Rack.objects.create(name="Rack B", area=area_b)

    response = api_client.get(f"/api/v1/dcim/racks/?area={area_a.id}")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == str(rack_a.id)


@pytest.mark.django_db
def test_device_configuration_latest_returns_most_recent_configuration(api_client):
    _, _, device = _device_inventory("dist-01", "192.0.2.21")
    older = _config(device, "hostname old\n", timezone.now() - timedelta(hours=1))
    newer = _config(device, "hostname new\n", timezone.now())

    response = api_client.get(f"/api/v1/dcim/devices/{device.id}/configurations/latest/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(newer.id)
    assert payload["device"] == str(device.id)
    assert payload["size"] == len("hostname new\n")
    assert payload["id"] != str(older.id)


@pytest.mark.django_db
def test_device_configuration_diff_returns_unified_diff(api_client):
    _, _, device = _device_inventory("core-01", "192.0.2.22")
    old = _config(device, "interface Gi1/0/1\n description old\n", timezone.now() - timedelta(hours=1))
    new = _config(device, "interface Gi1/0/1\n description new\n", timezone.now())

    response = api_client.get(
        f"/api/v1/dcim/devices/{device.id}/configurations/{new.id}/diff/{old.id}/"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["from"] == str(old.id)
    assert payload["to"] == str(new.id)
    assert "--- previous" in payload["diff"]
    assert "+++ current" in payload["diff"]
    assert "- description old" in payload["diff"]
    assert "+ description new" in payload["diff"]
