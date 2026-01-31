from pathlib import Path

import pytest
from django.conf import settings

from dcim.choices import DevicePlatformChoices, InterfaceStatusChoices
from dcim.models import (
    Area,
    Device,
    DeviceRuntimeStatus,
    DeviceType,
    DeviceModule,
    Organization,
    Site,
    Vendor,
    Interface,
)
from network.choices import CliCommandsChoices as cli
from network.services.sync_service import SyncService


FIXTURE_DIR = Path(settings.BASE_DIR) / "network" / "tests" / "fixtures" / "nxos"


def _load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


@pytest.fixture()
def nxos_device(db):
    org = Organization.objects.create(name="Test Org")
    site = Site.objects.create(name="Berlin", organization=org)
    area = Area.objects.create(name="A101", site=site)
    vendor = Vendor.objects.create(name="Cisco")
    device_type = DeviceType.objects.create(
        model="N9K-C93180YC-FX",
        platform=DevicePlatformChoices.NX_OS,
        vendor=vendor,
    )
    device = Device.objects.create(
        name="bppsw01-a587-b4",
        management_ip="10.20.30.40",
        site=site,
        area=area,
        device_type=device_type,
    )
    DeviceRuntimeStatus.objects.create(device=device)
    return device


@pytest.mark.django_db
def test_parse_nxos_textfsm_outputs(nxos_device):
    service = SyncService(site=nxos_device.site)
    results = {
        cli.VERSION_CMD: {"raw": _load_fixture("show_version.txt")},
        cli.INVENTORY_CMD: {"raw": _load_fixture("show_inventory.txt")},
        cli.IF_STATUS_CMD: {"raw": _load_fixture("show_interface_status.txt")},
        cli.IF_DESC_CMD: {"raw": _load_fixture("show_interface_description.txt")},
        cli.IF_IP_BRIEF_CMD: {"raw": _load_fixture("show_ip_interface_brief.txt")},
        cli.PORTCHANNEL_SUMMARY_NXOS_CMD: {"raw": _load_fixture("show_port_channel_summary.txt")},
        cli.IF_TRANSCEIVER_CMD: {"raw": _load_fixture("show_interface_transceiver.txt")},
    }

    service._parse_results(nxos_device, results)

    for command, result in results.items():
        if command == cli.IF_IP_BRIEF_CMD:
            continue
        parsed = result.get("parsed")
        assert parsed, f"Expected parsed output for {command}"


@pytest.mark.django_db
def test_apply_version_sets_serial_and_uptime(nxos_device):
    service = SyncService(site=nxos_device.site)
    results = {cli.VERSION_CMD: {"raw": _load_fixture("show_version.txt")}}
    service._parse_results(nxos_device, results)

    runtime = DeviceRuntimeStatus.objects.get(device=nxos_device)
    service._apply_version(nxos_device, runtime, results[cli.VERSION_CMD])

    nxos_device.refresh_from_db()
    assert nxos_device.serial_number == "FDO21481L7N"
    assert nxos_device.uptime is not None
    assert nxos_device.image_version and "10.3" in nxos_device.image_version


@pytest.mark.django_db
def test_apply_inventory_creates_modules(nxos_device):
    service = SyncService(site=nxos_device.site)
    results = {cli.INVENTORY_CMD: {"raw": _load_fixture("show_inventory.txt")}}
    service._parse_results(nxos_device, results)

    service._apply_inventory(nxos_device, results[cli.INVENTORY_CMD])

    assert DeviceModule.objects.filter(
        device=nxos_device, name="Chassis", serial_number="FDO26042T79"
    ).exists()
    assert DeviceModule.objects.filter(
        device=nxos_device, name="Power Supply 1"
    ).exists()


@pytest.mark.django_db
def test_apply_interfaces_updates_status_speed_and_lag(nxos_device):
    service = SyncService(site=nxos_device.site)
    results = {
        cli.IF_STATUS_CMD: {"raw": _load_fixture("show_interface_status.txt")},
        cli.IF_DESC_CMD: {"raw": _load_fixture("show_interface_description.txt")},
        cli.IF_IP_BRIEF_CMD: {"raw": _load_fixture("show_ip_interface_brief.txt")},
        cli.PORTCHANNEL_SUMMARY_NXOS_CMD: {"raw": _load_fixture("show_port_channel_summary.txt")},
    }
    service._parse_results(nxos_device, results)

    service._apply_interfaces(
        device=nxos_device,
        status_result=results[cli.IF_STATUS_CMD],
        desc_result=results[cli.IF_DESC_CMD],
        ip_result=results[cli.IF_IP_BRIEF_CMD],
        po_result=results[cli.PORTCHANNEL_SUMMARY_NXOS_CMD],
    )

    eth = Interface.objects.get(device=nxos_device, name="Eth1/5")
    assert eth.status == InterfaceStatusChoices.CONNECTED
    assert eth.speed == 10000
    assert eth.speed_mode == "10G"

    trunk = Interface.objects.get(device=nxos_device, name="Eth1/49")
    assert trunk.is_trunk is True

    member = Interface.objects.get(device=nxos_device, name="Eth1/53")
    assert member.lag is not None
    assert member.lag.name == "Po1"


@pytest.mark.django_db
def test_apply_transceivers_creates_modules(nxos_device):
    service = SyncService(site=nxos_device.site)
    results = {cli.IF_TRANSCEIVER_CMD: {"raw": _load_fixture("show_interface_transceiver.txt")}}
    service._parse_results(nxos_device, results)

    service._apply_transceivers(nxos_device, results[cli.IF_TRANSCEIVER_CMD])

    assert DeviceModule.objects.filter(
        device=nxos_device,
        name="Transceiver Ethernet1/1",
        serial_number="FNS17060KAQ",
    ).exists()
