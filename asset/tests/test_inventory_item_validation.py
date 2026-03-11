import pytest
from django.core.exceptions import ValidationError

from asset.models import InventoryItem
from dcim.choices import DevicePlatformChoices
from dcim.models import (
    Area,
    Device,
    DeviceModule,
    DeviceType,
    Organization,
    Site,
    Vendor,
)


@pytest.fixture()
def storage_validation_context(db):
    org = Organization.objects.create(name="Storage Validation Org")
    site = Site.objects.create(name="Berlin", organization=org)
    area = Area.objects.create(name="A101", site=site)
    vendor = Vendor.objects.create(name="Cisco")
    device_type = DeviceType.objects.create(
        model="C9300-48P",
        platform=DevicePlatformChoices.IOS_XE,
        vendor=vendor,
    )
    return {"site": site, "area": area, "device_type": device_type}


def _base_storage_item(*, site, area, serial_number):
    return InventoryItem(
        designation=InventoryItem.Designation.UPLINK_MODULE,
        model="C9300-NM-8X",
        site=site,
        area=area,
        serial_number=serial_number,
    )


@pytest.mark.django_db
def test_storage_item_allows_duplicate_serial_with_device(
    storage_validation_context,
):
    site = storage_validation_context["site"]
    area = storage_validation_context["area"]
    device_type = storage_validation_context["device_type"]
    Device.objects.create(
        name="prod-device",
        management_ip="10.1.1.1",
        site=site,
        area=area,
        device_type=device_type,
        serial_number="SER-500",
    )

    item = _base_storage_item(site=site, area=area, serial_number="SER-500")
    item.full_clean()
    item.save()
    assert InventoryItem.objects.filter(serial_number="SER-500").exists()


@pytest.mark.django_db
def test_storage_item_rejects_duplicate_serial_in_production_module(
    storage_validation_context,
):
    site = storage_validation_context["site"]
    area = storage_validation_context["area"]
    device_type = storage_validation_context["device_type"]
    device = Device.objects.create(
        name="prod-device-mod",
        management_ip="10.1.1.2",
        site=site,
        area=area,
        device_type=device_type,
    )
    DeviceModule.objects.create(
        device=device,
        name="Uplink Module",
        serial_number="SER-501",
    )

    item = _base_storage_item(site=site, area=area, serial_number="SER-501")
    with pytest.raises(ValidationError) as excinfo:
        item.full_clean()

    assert "Production module" in str(excinfo.value)
