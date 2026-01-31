from pathlib import Path

import pytest
from django.conf import settings

from dcim.choices import DevicePlatformChoices
from dcim.models import (
    Area,
    Device,
    DeviceRuntimeStatus,
    DeviceType,
    DeviceModule,
    Organization,
    Site,
    Vendor,
)
from network.choices import CliCommandsChoices as cli
from network.services.sync_service import SyncService


FIXTURE_DIR = Path(settings.BASE_DIR) / "network" / "tests" / "fixtures" / "aci"


def _load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


@pytest.fixture()
def aci_device(db):
    org = Organization.objects.create(name="Test Org")
    site = Site.objects.create(name="Berlin", organization=org)
    area = Area.objects.create(name="A101", site=site)
    vendor = Vendor.objects.create(name="Cisco")
    device_type = DeviceType.objects.create(
        model="N9K-C93108TC-FX",
        platform=DevicePlatformChoices.NX_OS,
        vendor=vendor,
    )
    device = Device.objects.create(
        name="bleaf103-a324-43",
        management_ip="10.50.60.70",
        site=site,
        area=area,
        device_type=device_type,
    )
    DeviceRuntimeStatus.objects.create(device=device)
    return device


@pytest.mark.django_db
def test_apply_version_parses_aci_output(aci_device):
    service = SyncService(site=aci_device.site)
    result = {cli.VERSION_CMD: {"raw": _load_fixture("show_version.txt")}}

    runtime = DeviceRuntimeStatus.objects.get(device=aci_device)
    service._apply_version(aci_device, runtime, result[cli.VERSION_CMD])

    aci_device.refresh_from_db()
    assert aci_device.serial_number == "FDO23030PM7"
    assert aci_device.uptime is not None
    assert aci_device.image_version and "16.0" in aci_device.image_version


@pytest.mark.django_db
def test_apply_inventory_creates_modules(aci_device):
    service = SyncService(site=aci_device.site)
    results = {cli.INVENTORY_CMD: {"raw": _load_fixture("show_inventory.txt")}}
    service._parse_results(aci_device, results)

    service._apply_inventory(aci_device, results[cli.INVENTORY_CMD])

    assert DeviceModule.objects.filter(
        device=aci_device, name="Chassis", serial_number="FDO23030PM7"
    ).exists()
    assert DeviceModule.objects.filter(
        device=aci_device, name__icontains="power supply"
    ).exists()


@pytest.mark.django_db
def test_apply_transceivers_skips_missing_serials(aci_device):
    service = SyncService(site=aci_device.site)
    results = {cli.IF_TRANSCEIVER_CMD: {"raw": _load_fixture("show_interface_transceiver.txt")}}
    service._parse_results(aci_device, results)

    service._apply_transceivers(aci_device, results[cli.IF_TRANSCEIVER_CMD])

    transceivers = DeviceModule.objects.filter(
        device=aci_device, name__startswith="Transceiver "
    )
    assert transceivers.count() == 2
    assert transceivers.filter(serial_number="FNS2302024J").exists()
    assert transceivers.filter(serial_number="FNS2302024C").exists()
