from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone

from dcim.models import Area, Device, DeviceRole, DeviceType, Interface, Organization, Site, Tag, Vendor
from topology.models import TopologyNeighbor
from topology.services.topology_service import TopologyService


def _device(name: str, ip: str, *, site: Site, area: Area):
    vendor, _ = Vendor.objects.get_or_create(name="Cisco")
    device_type, _ = DeviceType.objects.get_or_create(vendor=vendor, model=f"{name}-model")
    role, _ = DeviceRole.objects.get_or_create(name="Access")
    return Device.objects.create(
        name=name,
        management_ip=ip,
        site=site,
        area=area,
        device_type=device_type,
        role=role,
        status="active",
    )


@pytest.mark.django_db
def test_upsert_neighbor_creates_and_then_updates_existing_neighbor():
    organization = Organization.objects.create(name="Topo Org")
    site = Site.objects.create(name="Berlin", organization=organization, domain="example.com")
    area = Area.objects.create(name="Room 1", site=site)
    source = _device("sw01.example.com", "192.0.2.31", site=site, area=area)
    neighbor_device = _device("sw02.example.com", "192.0.2.32", site=site, area=area)
    local_interface = Interface.objects.create(name="Gi1/0/1", device=source)

    with patch("topology.services.topology_service.timezone.now", return_value=timezone.now()) as mock_now:
        created = TopologyService.upsert_neighbor(
            device=source,
            local_interface=local_interface,
            neighbor_name="sw02",
            neighbor_interface="Gi1/0/2",
            protocol="cdp",
            platform="IOS-XE",
            capabilities="Switch",
        )
        updated = TopologyService.upsert_neighbor(
            device=source,
            local_interface=local_interface,
            neighbor_name="sw02",
            neighbor_interface="Gi1/0/2",
            protocol="cdp",
            platform="NX-OS",
            capabilities="Router",
        )

    assert created.pk == updated.pk
    assert TopologyNeighbor.objects.count() == 1
    assert updated.neighbor_name == "sw02.example.com"
    assert updated.neighbor_device == neighbor_device
    assert updated.platform == "NX-OS"
    assert updated.capabilities == "Router"
    assert updated.last_seen == mock_now.return_value


@pytest.mark.django_db
def test_upsert_neighbor_requires_neighbor_name_and_interface():
    organization = Organization.objects.create(name="Topo Org Error")
    site = Site.objects.create(name="Munich", organization=organization)
    area = Area.objects.create(name="Room A", site=site)
    device = _device("edge-01", "192.0.2.33", site=site, area=area)

    with pytest.raises(ValueError):
        TopologyService.upsert_neighbor(
            device=device,
            local_interface=None,
            neighbor_name="",
            neighbor_interface="",
            protocol="lldp",
        )


@pytest.mark.django_db
def test_topology_collect_rejects_async_site_filter():
    stdout = StringIO()
    stderr = StringIO()

    with patch("topology.management.commands.topology_collect.collect_topology_neighbors.delay") as mock_delay:
        call_command("topology_collect", site_name="Berlin", run_async=True, stdout=stdout, stderr=stderr)

    assert "--site and --tag are only supported for inline runs." in stderr.getvalue()
    mock_delay.assert_not_called()


@pytest.mark.django_db
def test_topology_collect_inline_reports_success_and_failure_counts():
    organization = Organization.objects.create(name="Collect Org")
    site = Site.objects.create(name="Frankfurt", organization=organization)
    area = Area.objects.create(name="Row A", site=site)
    ok_tag = Tag.objects.create(name="backbone")
    ok_device = _device("core-01", "192.0.2.41", site=site, area=area)
    fail_device = _device("core-02", "192.0.2.42", site=site, area=area)
    ok_device.tags.add(ok_tag)
    fail_device.tags.add(ok_tag)
    stdout = StringIO()

    def _collect(device):
        return device.name == "core-01"

    with patch(
        "topology.management.commands.topology_collect.get_eligible_devices",
        return_value=[ok_device, fail_device],
    ):
        with patch(
            "topology.management.commands.topology_collect.collect_neighbors_for_device",
            side_effect=_collect,
        ):
            call_command(
                "topology_collect",
                site_name="Frankfurt",
                tag_name="backbone",
                threads=1,
                stdout=stdout,
            )

    output = stdout.getvalue()
    assert "[OK] core-01" in output
    assert "[FAIL] core-02" in output
    assert "Success: 1, Failed: 1" in output
