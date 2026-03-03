from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client

from core.organization_views import _build_area_tree
from dcim.models import (
    Area,
    Device,
    DeviceRole,
    DeviceStackMember,
    DeviceType,
    Organization,
    Rack,
    Site,
    Vendor,
)


def _create_user(*, can_view_device=False):
    user = get_user_model().objects.create_user(username="viewer", password="pass")
    if can_view_device:
        permission = Permission.objects.get(codename="view_device")
        user.user_permissions.add(permission)
    return user


def _inventory():
    organization = Organization.objects.create(name="Org")
    site = Site.objects.create(name="Berlin", organization=organization)
    area = Area.objects.create(name="Room A", site=site)
    rack = Rack.objects.create(name="Rack-1", area=area, u_height=10)
    vendor = Vendor.objects.create(name="Cisco")
    device_type = DeviceType.objects.create(
        vendor=vendor,
        model="C9300",
        u_height=Decimal("2.0"),
        default_ac_power_supply_watts=250,
        weight=Decimal("7.5"),
    )
    role = DeviceRole.objects.create(name="Access")
    return organization, site, area, rack, device_type, role


@pytest.mark.django_db
def test_build_area_tree_marks_selected_branch_open():
    organization = Organization.objects.create(name="Tree Org")
    site = Site.objects.create(name="Tree Site", organization=organization)
    root = Area.objects.create(name="Root", site=site)
    branch = Area.objects.create(name="Branch", site=site, parent=root)
    leaf = Area.objects.create(name="Leaf", site=site, parent=branch)

    tree = _build_area_tree(Area.objects.filter(site=site), selected_area_id=leaf.id)

    assert len(tree) == 1
    assert tree[0]["area"] == root
    assert tree[0]["open"] is True
    assert tree[0]["children"][0]["area"] == branch
    assert tree[0]["children"][0]["open"] is True
    assert tree[0]["children"][0]["children"][0]["area"] == leaf
    assert tree[0]["children"][0]["children"][0]["open"] is True


@pytest.mark.django_db
def test_site_create_returns_hx_redirect_for_new_site():
    organization = Organization.objects.create(name="Org Create")
    user = _create_user()
    client = Client()
    client.force_login(user)

    response = client.post(
        "/organization/sites/create/",
        {
            "name": "Munich",
            "domain": "example.net",
            "description": "New site",
        },
    )

    site = Site.objects.get(name="Munich", organization=organization)
    assert response.status_code == 204
    assert response["HX-Redirect"] == f"/organization/?site={site.id}"


@pytest.mark.django_db
def test_area_delete_with_children_returns_error_and_keeps_area():
    organization = Organization.objects.create(name="Org Delete")
    site = Site.objects.create(name="Frankfurt", organization=organization)
    parent = Area.objects.create(name="Floor 1", site=site)
    Area.objects.create(name="Room 101", site=site, parent=parent)
    user = _create_user()
    client = Client()
    client.force_login(user)

    response = client.post(f"/organization/areas/{parent.id}/delete/")

    assert response.status_code == 200
    assert Area.objects.filter(pk=parent.pk).exists() is True
    assert b"Cannot delete an area that has child areas." in response.content


@pytest.mark.django_db
def test_rack_detail_view_builds_layout_for_users_with_device_permission():
    _, _, area, rack, device_type, role = _inventory()
    user = _create_user(can_view_device=True)
    client = Client()
    client.force_login(user)

    device = Device.objects.create(
        name="stack-01",
        management_ip="192.0.2.10",
        site=area.site,
        area=area,
        rack=rack,
        device_type=device_type,
        role=role,
        is_stacked=True,
        position=Decimal("3.0"),
        status="active",
    )
    DeviceStackMember.objects.create(
        device=device,
        switch_number=1,
        role="active",
        mac_address="00:11:22:33:44:55",
        state="ready",
    )
    DeviceStackMember.objects.create(
        device=device,
        switch_number=2,
        role="standby",
        mac_address="00:11:22:33:44:56",
        state="ready",
    )

    response = client.get(f"/organization/racks/{rack.id}/")
    layout = response.context["layout"]
    head_unit = next(unit for unit in layout if unit["device"] == device)

    assert response.status_code == 200
    assert response.context["show_devices"] is True
    assert response.context["has_positions"] is True
    assert head_unit["unit"] == 6
    assert head_unit["height"] == 4
    assert head_unit["stack_count"] == 2
    assert response.context["rack_power_watts"] == 500


@pytest.mark.django_db
def test_rack_detail_view_hides_layout_without_device_permission():
    _, _, area, rack, device_type, role = _inventory()
    user = _create_user(can_view_device=False)
    client = Client()
    client.force_login(user)

    Device.objects.create(
        name="edge-01",
        management_ip="192.0.2.11",
        site=area.site,
        area=area,
        rack=rack,
        device_type=device_type,
        role=role,
        position=Decimal("1.0"),
        status="active",
    )

    response = client.get(f"/organization/racks/{rack.id}/")

    assert response.status_code == 200
    assert response.context["show_devices"] is False
    assert response.context["layout"] == []
    assert response.context["has_positions"] is False
