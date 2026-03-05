from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone

from dcim.models import Area, DeviceType, Organization, Rack, Site, Tag, Vendor
from network.models.discovery import DiscoveryCandidate
from network.services.auto_assignment_service import AutoAssignmentService


def _candidate(hostname: str):
    organization = Organization.objects.create(name=f"{hostname}-org")
    site = Site.objects.create(name=f"{hostname}-site", organization=organization)
    return DiscoveryCandidate.objects.create(
        site=site,
        ip_address=f"192.0.2.{DiscoveryCandidate.objects.count() + 60}",
        hostname=hostname,
        alive=True,
        reachable_ssh=True,
        last_seen=timezone.now(),
    )


@pytest.mark.django_db
def test_parse_snmp_location_extracts_area_rack_and_unit():
    service = AutoAssignmentService(_candidate("bcsw-01"))

    area, rack, unit = service._parse_snmp_location("System Location: RoomA Rack12 U14")

    assert area == "RoomA"
    assert rack == "Rack12"
    assert unit == Decimal("14")


@pytest.mark.django_db
def test_parse_snmp_location_maps_vm_hostnames_to_vcenter():
    service = AutoAssignmentService(_candidate("tenant-vm-esx01"))

    area, rack, unit = service._parse_snmp_location("RoomB Rack21 U4")

    assert area == "VCenter"
    assert rack == "Rack21"
    assert unit == Decimal("4")


@pytest.mark.django_db
def test_parse_aci_location_uses_hostname_fallback():
    service = AutoAssignmentService(_candidate("fab-b2-17-leaf01"))
    service._is_aci = True

    area, rack, unit = service._parse_snmp_location("")

    assert area == "b2"
    assert rack == "Rack17"
    assert unit is None


@pytest.mark.django_db
def test_select_position_prefers_requested_unit_when_free():
    organization = Organization.objects.create(name="Rack Org")
    site = Site.objects.create(name="Rack Site", organization=organization)
    area = Area.objects.create(name="Area 1", site=site)
    rack = Rack.objects.create(name="Rack A", area=area, u_height=10, occupied_units=[1.0, 2.0])
    service = AutoAssignmentService(_candidate("edge-01"))

    position = service._select_position(rack, Decimal("5"), required_units=2)

    assert position == Decimal("5")


@pytest.mark.django_db
def test_select_position_picks_random_free_candidate_when_requested_is_occupied():
    organization = Organization.objects.create(name="Rack Org 2")
    site = Site.objects.create(name="Rack Site 2", organization=organization)
    area = Area.objects.create(name="Area 2", site=site)
    rack = Rack.objects.create(name="Rack B", area=area, u_height=6, occupied_units=[2.0, 3.0, 4.0])
    service = AutoAssignmentService(_candidate("edge-02"))

    with patch("network.services.auto_assignment_service.random.choice", return_value=5):
        position = service._select_position(rack, Decimal("3"), required_units=1)

    assert position == Decimal("5")


@pytest.mark.django_db
def test_resolve_tags_returns_existing_tags_for_hostname_patterns():
    service = AutoAssignmentService(_candidate("bmsw-leaf01"))
    expected = {
        "reachability_check_tag",
        "discovered-new",
        "management",
        "config_backup_tag",
        "aci_fabric",
    }
    for name in expected:
        Tag.objects.create(name=name)

    tags = service._resolve_tags()

    assert {tag.name for tag in tags} == expected


@pytest.mark.django_db
def test_select_model_from_inventory_prefers_vendor_matching_device_type():
    vendor = Vendor.objects.create(name="Cisco")
    DeviceType.objects.create(vendor=vendor, model="C9300-48P")
    inventory = [
        {"name": "Transceiver 1", "pid": "SFP-10G-SR"},
        {"name": "Chassis", "pid": "C9300-48P"},
    ]

    model = AutoAssignmentService._select_model_from_inventory(inventory, vendor=vendor)

    assert model == "C9300-48P"


@pytest.mark.django_db
def test_parse_stack_members_normalizes_role_and_state():
    service = AutoAssignmentService(_candidate("stack-01"))
    raw = """
*    1 Active   0011.2233.4455 15 V01 Ready
     2 Standby  0011.2233.4466 14 V01 Provisioned
    """

    members = service._parse_stack_members(raw)

    assert members == [
        {
            "switch_number": 1,
            "role": "active",
            "mac_address": "0011.2233.4455",
            "priority": 15,
            "version": "V01",
            "state": "ready",
        },
        {
            "switch_number": 2,
            "role": "standby",
            "mac_address": "0011.2233.4466",
            "priority": 14,
            "version": "V01",
            "state": "provisioned",
        },
    ]
