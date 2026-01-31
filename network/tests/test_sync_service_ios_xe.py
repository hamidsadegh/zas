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


FIXTURE_DIR = Path(settings.BASE_DIR) / "network" / "tests" / "fixtures" / "ios_xe"


def _load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


@pytest.fixture()
def ios_xe_device(db):
    org = Organization.objects.create(name="Test Org")
    site = Site.objects.create(name="Berlin", organization=org)
    area = Area.objects.create(name="A101", site=site)
    vendor = Vendor.objects.create(name="Cisco")
    device_type = DeviceType.objects.create(
        model="C9300-48P",
        platform=DevicePlatformChoices.IOS_XE,
        vendor=vendor,
    )
    device = Device.objects.create(
        name="bcsw01-a179d-01.dwelle.de",
        management_ip="10.10.10.10",
        site=site,
        area=area,
        device_type=device_type,
    )
    DeviceRuntimeStatus.objects.create(device=device)
    return device


@pytest.mark.django_db
def test_parse_ios_xe_textfsm_outputs(ios_xe_device):
    service = SyncService(site=ios_xe_device.site)
    results = {
        cli.VERSION_CMD: {"raw": _load_fixture("show_version.txt")},
        cli.INVENTORY_CMD: {"raw": _load_fixture("show_inventory.txt")},
        cli.IF_STATUS_CMD: {"raw": _load_fixture("show_interface_status.txt")},
        cli.IF_DESC_CMD: {"raw": _load_fixture("show_interface_description.txt")},
        cli.IF_IP_BRIEF_CMD: {"raw": _load_fixture("show_ip_interface_brief.txt")},
        cli.PORTCHANNEL_SUMMARY_ISO_CMD: {"raw": _load_fixture("show_etherchannel_summary.txt")},
    }

    service._parse_results(ios_xe_device, results)

    for command, result in results.items():
        parsed = result.get("parsed")
        assert parsed, f"Expected parsed output for {command}"


@pytest.mark.django_db
def test_apply_version_sets_serial_and_uptime(ios_xe_device):
    service = SyncService(site=ios_xe_device.site)
    results = {cli.VERSION_CMD: {"raw": _load_fixture("show_version.txt")}}
    service._parse_results(ios_xe_device, results)

    runtime = DeviceRuntimeStatus.objects.get(device=ios_xe_device)
    service._apply_version(ios_xe_device, runtime, results[cli.VERSION_CMD])

    ios_xe_device.refresh_from_db()
    assert ios_xe_device.serial_number == "FOC2340X01D"
    assert ios_xe_device.uptime is not None
    assert ios_xe_device.image_version is not None


@pytest.mark.django_db
def test_apply_inventory_creates_modules(ios_xe_device):
    service = SyncService(site=ios_xe_device.site)
    results = {cli.INVENTORY_CMD: {"raw": _load_fixture("show_inventory.txt")}}
    service._parse_results(ios_xe_device, results)

    service._apply_inventory(ios_xe_device, results[cli.INVENTORY_CMD])

    assert DeviceModule.objects.filter(
        device=ios_xe_device, name="Switch 2", serial_number="FOC2340X01D"
    ).exists()
    assert DeviceModule.objects.filter(
        device=ios_xe_device, name="Switch 2 - Power Supply A"
    ).exists()


@pytest.mark.django_db
def test_apply_interfaces_updates_status_speed_and_lag(ios_xe_device):
    service = SyncService(site=ios_xe_device.site)
    results = {
        cli.IF_STATUS_CMD: {"raw": _load_fixture("show_interface_status.txt")},
        cli.IF_DESC_CMD: {"raw": _load_fixture("show_interface_description.txt")},
        cli.IF_IP_BRIEF_CMD: {"raw": _load_fixture("show_ip_interface_brief.txt")},
        cli.PORTCHANNEL_SUMMARY_ISO_CMD: {"raw": _load_fixture("show_etherchannel_summary.txt")},
    }
    service._parse_results(ios_xe_device, results)

    service._apply_interfaces(
        device=ios_xe_device,
        status_result=results[cli.IF_STATUS_CMD],
        desc_result=results[cli.IF_DESC_CMD],
        ip_result=results[cli.IF_IP_BRIEF_CMD],
        po_result=results[cli.PORTCHANNEL_SUMMARY_ISO_CMD],
    )

    gi = Interface.objects.get(device=ios_xe_device, name="Gi2/0/3")
    assert gi.status == InterfaceStatusChoices.CONNECTED
    assert gi.speed == 1000
    assert gi.speed_mode == "a-1000"
    assert gi.duplex == "full"
    assert gi.is_trunk is True

    vlan = Interface.objects.get(device=ios_xe_device, name="Vlan49")
    assert vlan.ip_address == "192.168.49.125"
    assert vlan.status == InterfaceStatusChoices.UP

    member = Interface.objects.get(device=ios_xe_device, name="Fo2/1/1")
    assert member.lag is not None
    assert member.lag.name == "Po1"


@pytest.mark.django_db
def test_apply_stack_members_from_raw(ios_xe_device):
    service = SyncService(site=ios_xe_device.site)
    result = {"raw": _load_fixture("show_switch.txt")}

    service._apply_stack_members(ios_xe_device, result)

    ios_xe_device.refresh_from_db()
    assert ios_xe_device.is_stacked is True
    assert ios_xe_device.stack_members.count() == 2
    assert ios_xe_device.stack_members.filter(switch_number=2).exists()
    assert ios_xe_device.stack_members.filter(switch_number=3).exists()
