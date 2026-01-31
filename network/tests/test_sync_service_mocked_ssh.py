from pathlib import Path
from unittest.mock import patch

import pytest
from django.conf import settings

from accounts.models.credentials import SSHCredential
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


IOS_FIXTURE_DIR = Path(settings.BASE_DIR) / "network" / "tests" / "fixtures" / "ios_xe"


def _load_ios_fixture(name: str) -> str:
    return (IOS_FIXTURE_DIR / name).read_text(encoding="utf-8")


@pytest.fixture()
def ios_xe_device_with_cred(db):
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
    SSHCredential.objects.create(
        site=site,
        name="default",
        type="ssh",
        ssh_username="user",
        ssh_password="pass",
        ssh_port=22,
    )
    return device


class FakeNetmikoAdapter:
    def __init__(self, device, allow_autodetect=False):
        self.device = device
        self.allow_autodetect = allow_autodetect

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, exc_tb):
        return False

    def run_command_raw(self, command: str) -> dict:
        mapping = {
            cli.VERSION_CMD: _load_ios_fixture("show_version.txt"),
            cli.INVENTORY_CMD: _load_ios_fixture("show_inventory.txt"),
            cli.IF_STATUS_CMD: _load_ios_fixture("show_interface_status.txt"),
            cli.IF_DESC_CMD: _load_ios_fixture("show_interface_description.txt"),
            cli.IF_IP_BRIEF_CMD: _load_ios_fixture("show_ip_interface_brief.txt"),
            cli.PORTCHANNEL_SUMMARY_ISO_CMD: _load_ios_fixture("show_etherchannel_summary.txt"),
            cli.STACK_SWITCH_CMD: _load_ios_fixture("show_switch.txt"),
        }
        return {"raw": mapping.get(command, ""), "parsed": None, "error": None}


@pytest.mark.django_db
def test_sync_device_with_mocked_ssh(ios_xe_device_with_cred):
    service = SyncService(site=ios_xe_device_with_cred.site)
    with patch("network.services.sync_service.NetmikoAdapter", FakeNetmikoAdapter):
        result = service.sync_device(ios_xe_device_with_cred, include_config=False)

    assert result["success"] is True

    device = Device.objects.get(id=ios_xe_device_with_cred.id)
    assert device.serial_number == "FOC2340X01D"

    gi = Interface.objects.get(device=device, name="Gi2/0/3")
    assert gi.status == InterfaceStatusChoices.CONNECTED
    assert gi.speed == 1000

    assert DeviceModule.objects.filter(
        device=device, name="Switch 2", serial_number="FOC2340X01D"
    ).exists()


@pytest.mark.django_db
def test_sync_device_retry_on_failure(ios_xe_device_with_cred):
    call_count = {"value": 0}

    class FlakyNetmikoAdapter(FakeNetmikoAdapter):
        def __enter__(self):
            call_count["value"] += 1
            if call_count["value"] == 1:
                raise RuntimeError("SSH failed")
            return self

    service = SyncService(site=ios_xe_device_with_cred.site)
    with patch("network.services.sync_service.NetmikoAdapter", FlakyNetmikoAdapter):
        result = service.sync_device(ios_xe_device_with_cred, include_config=False)

    assert call_count["value"] == 2
    assert result["success"] is True

