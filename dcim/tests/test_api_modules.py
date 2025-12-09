import pytest
from dcim.models import Vendor, Device, Organization, Area, Site, DeviceModule
from api.v1.dcim.serializers import DeviceSerializer


@pytest.mark.django_db
def test_device_serializer_includes_modules():
    org = Organization.objects.create(name="Org1")
    site = Site.objects.create(name="Site1", organization=org)
    area = Area.objects.create(name="Area1", site=site)
    vendor = Vendor.objects.create(name="Cisco")
    device = Device.objects.create(
        name="Device-1",
        management_ip="10.0.0.1",
        site=site,
        area=area,
        vendor=vendor,
    )
    DeviceModule.objects.create(
        device=device,
        vendor=vendor,
        name="Supervisor",
        serial_number="SN123",
    )
    serializer = DeviceSerializer(instance=device)
    modules = serializer.data.get("modules", [])

    assert len(modules) == 1
    assert modules[0]["name"] == "Supervisor"
    assert modules[0]["serial_number"] == "SN123"
    assert serializer.data["reachable_ssh"] is False
    assert serializer.data["reachable_ping"] is False
    assert serializer.data["reachable_snmp"] is False
    assert serializer.data["reachable_netconf"] is False
