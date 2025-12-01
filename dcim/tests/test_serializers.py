from types import SimpleNamespace

import pytest # type: ignore
from rest_framework import serializers # type: ignore

from dcim.models import Area, Device, DeviceType, Organization, Rack, Vendor
from dcim.serializers import DeviceSerializer


def _make_area(name, organization):
    return Area.objects.create(name=name, organization=organization)


def _make_rack(name, area, **kwargs):
    return Rack.objects.create(name=name, area=area, **kwargs)


@pytest.mark.django_db
def test_device_serializer_rack_queryset_uses_request_data():
    org = Organization.objects.create(name="Org One")
    area_a = _make_area("Area A", org)
    area_b = _make_area("Area B", org)
    rack_a1 = _make_rack("Rack A1", area_a, width=19, u_height=42, starting_unit =1, status='active')
    rack_a2 = _make_rack("Rack A2", area_a, width=19, u_height=42, starting_unit =1, status='active')
    _make_rack("Rack B1", area_b)

    request = SimpleNamespace(data={"area": area_a.id}, query_params={})

    serializer = DeviceSerializer(context={"request": request})

    queryset = serializer.fields["rack"].queryset
    assert set(queryset) == {rack_a1, rack_a2}


@pytest.mark.django_db
def test_device_serializer_rack_queryset_uses_instance_area():
    org = Organization.objects.create(name="Org Two")
    area_a = _make_area("Area A", org)
    _make_area("Area B", org)
    rack_a1 = _make_rack("Rack A1", area_a)
    rack_a2 = _make_rack("Rack A2", area_a)

    device = Device.objects.create(
        name="Device A",
        management_ip="10.0.0.1",
        organization=org,
        area=area_a,
        rack=rack_a1,
    )

    serializer = DeviceSerializer(instance=device)

    queryset = serializer.fields["rack"].queryset
    assert set(queryset) == {rack_a1, rack_a2}


@pytest.mark.django_db
def test_device_serializer_validate_rejects_rack_from_other_area():
    org = Organization.objects.create(name="Org Three")
    area_a = _make_area("Area A", org)
    area_b = _make_area("Area B", org)
    rack_a = _make_rack("Rack A", area_a)
    rack_b = _make_rack("Rack B", area_b)

    serializer = DeviceSerializer()

    with pytest.raises(serializers.ValidationError) as excinfo:
        serializer.validate({"area": area_a, "rack": rack_b})

    assert "Rack" in str(excinfo.value)
    assert "does not belong to area" in str(excinfo.value)

    valid = serializer.validate({"area": area_a, "rack": rack_a})
    assert valid["rack"] == rack_a
@pytest.mark.django_db
def test_device_serializer_includes_related_display_fields():
    org = Organization.objects.create(name="Org Base")
    vendor = Vendor.objects.create(name="Cisco")
    dtype = DeviceType.objects.create(vendor=vendor, model="C9300")
    device = Device.objects.create(
        name="bcsw01",
        management_ip="192.168.10.10",
        organization=org,
        vendor=vendor,
        device_type=dtype,
        status="active",
    )

    serializer = DeviceSerializer(instance=device)
    data = serializer.data

    assert data["name"] == "bcsw01"
    assert data["management_ip"] == "192.168.10.10"
    assert data["vendor_name"] == "Cisco"
    assert data["device_type_name"] == "C9300"
