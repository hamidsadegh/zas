import pytest # pyright: ignore[reportMissingImports]
from django.utils import timezone
from dcim.models import (
    Organization, Area, Vendor, DeviceType, DeviceRole, Device
)

@pytest.mark.django_db
def test_device_creation():
    # Create base dependencies
    organization = Organization.objects.create(name="TestOrg")
    area = Area.objects.create(name="Berlin", organization=organization)
    vendor = Vendor.objects.create(name="Cisco")
    device_type = DeviceType.objects.create(vendor=vendor, model="C9300-48P")
    role = DeviceRole.objects.create(name="Access Switch")

    # Create device with all required foreign keys
    device = Device.objects.create(
        name="bcsw01-a324-46",
        management_ip="192.168.49.128",
        organization=organization,
        area=area,
        vendor=vendor,
        device_type=device_type,
        role=role,
        status="active",
    )

    # Assertions
    assert device.name == "bcsw01-a324-46"
    assert device.vendor.name == "Cisco"
    assert device.device_type.model == "C9300-48P"
    assert device.status == "active"
    assert device.created_at <= timezone.now()
