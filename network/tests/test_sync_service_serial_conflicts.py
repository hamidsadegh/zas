import pytest

from asset.models import InventoryItem
from dcim.choices import DevicePlatformChoices
from dcim.models import (
    Area,
    Device,
    DeviceModule,
    DeviceRuntimeStatus,
    DeviceType,
    Organization,
    Site,
    Vendor,
)
from network.services.sync_service import SyncService


@pytest.fixture()
def serial_conflict_context(db):
    org = Organization.objects.create(name="Serial Test Org")
    site = Site.objects.create(name="Berlin", organization=org)
    area = Area.objects.create(name="A101", site=site)
    vendor = Vendor.objects.create(name="Cisco")
    device_type = DeviceType.objects.create(
        model="C9300-48P",
        platform=DevicePlatformChoices.IOS_XE,
        vendor=vendor,
    )
    return {"site": site, "area": area, "device_type": device_type}


def _create_device(*, name, ip, site, area, device_type, serial=None):
    return Device.objects.create(
        name=name,
        management_ip=ip,
        site=site,
        area=area,
        device_type=device_type,
        serial_number=serial,
    )


@pytest.mark.django_db
def test_sync_inventory_duplicate_in_production_replaces_old_module(serial_conflict_context):
    site = serial_conflict_context["site"]
    area = serial_conflict_context["area"]
    device_type = serial_conflict_context["device_type"]
    old_device = _create_device(
        name="old-device",
        ip="10.0.0.1",
        site=site,
        area=area,
        device_type=device_type,
    )
    new_device = _create_device(
        name="new-device",
        ip="10.0.0.2",
        site=site,
        area=area,
        device_type=device_type,
    )
    DeviceModule.objects.create(
        device=old_device,
        name="Old Module",
        serial_number="MOD-100",
    )

    service = SyncService(site=site)
    service._apply_inventory(
        new_device,
        {"parsed": [{"name": "New Module", "sn": "MOD-100", "descr": "Moved module"}]},
    )

    assert DeviceModule.objects.filter(
        device=new_device,
        name="New Module",
        serial_number="MOD-100",
    ).exists()
    assert not DeviceModule.objects.filter(
        device=old_device,
        serial_number="MOD-100",
    ).exists()


@pytest.mark.django_db
def test_sync_inventory_duplicate_with_storage_deletes_storage_item(serial_conflict_context):
    site = serial_conflict_context["site"]
    area = serial_conflict_context["area"]
    device_type = serial_conflict_context["device_type"]
    device = _create_device(
        name="sync-device",
        ip="10.0.0.10",
        site=site,
        area=area,
        device_type=device_type,
    )
    InventoryItem.objects.create(
        designation="Uplink Module",
        model="C9300-NM-8X",
        site=site,
        area=area,
        serial_number="MOD-200",
    )

    service = SyncService(site=site)
    service._apply_inventory(
        device,
        {"parsed": [{"name": "Uplink Module", "sn": "MOD-200", "descr": "Detected"}]},
    )

    assert DeviceModule.objects.filter(
        device=device,
        name="Uplink Module",
        serial_number="MOD-200",
    ).exists()
    assert not InventoryItem.objects.filter(serial_number="MOD-200").exists()


@pytest.mark.django_db
def test_sync_version_keeps_newest_device_serial_and_removes_storage_item(
    serial_conflict_context,
):
    site = serial_conflict_context["site"]
    area = serial_conflict_context["area"]
    device_type = serial_conflict_context["device_type"]
    old_device = _create_device(
        name="old-device-serial",
        ip="10.0.0.11",
        site=site,
        area=area,
        device_type=device_type,
        serial="DEV-300",
    )
    new_device = _create_device(
        name="new-device-serial",
        ip="10.0.0.12",
        site=site,
        area=area,
        device_type=device_type,
    )
    runtime = DeviceRuntimeStatus.objects.create(device=new_device)
    InventoryItem.objects.create(
        designation="Chassis",
        model="C9300-48P",
        site=site,
        area=area,
        serial_number="DEV-300",
    )

    service = SyncService(site=site)
    service._apply_version(
        new_device,
        runtime,
        {"parsed": [{"serial": "DEV-300", "version": "17.9.1a"}], "raw": ""},
    )

    old_device.refresh_from_db()
    new_device.refresh_from_db()
    assert new_device.serial_number == "DEV-300"
    assert old_device.serial_number is None
    assert not InventoryItem.objects.filter(serial_number="DEV-300").exists()
