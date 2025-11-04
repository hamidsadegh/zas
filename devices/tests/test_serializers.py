# devices/tests/test_serializers.py

import pytest # pyright: ignore[reportMissingImports]
from devices.models import Organization, Vendor, Platform, DeviceType, Device
from devices.serializers import DeviceSerializer

@pytest.mark.django_db
def test_device_serializer_fields():
    org = Organization.objects.create(name="TestOrg")
    vendor = Vendor.objects.create(name="Cisco")
    platform = Platform.objects.create(name="IOS-XE", vendor=vendor)
    dtype = DeviceType.objects.create(vendor=vendor, model="C9300", category="catalyst")

    device = Device.objects.create(
        name="bcsw01",
        management_ip="192.168.10.10",
        organization=org,
        vendor=vendor,
        platform=platform,
        device_type=dtype,
        status="active",
    )

    serializer = DeviceSerializer(device)
    data = serializer.data

    assert data["name"] == "bcsw01"
    assert data["management_ip"] == "192.168.10.10"
    assert data["vendor_name"] == "Cisco"
    assert "status" in data
    assert data["device_type_name"] == "C9300"
