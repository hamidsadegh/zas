import random

import pytest

from dcim.choices import InterfaceStatusChoices
from dcim.models import (
    Area,
    Device,
    DeviceModule,
    DeviceRole,
    DeviceType,
    Interface,
    Organization,
    Rack,
    Site,
    Vendor,
)
from dcim.services.configuration_persistence_service import (
    ConfigurationPersistenceService,
)


@pytest.mark.django_db
def test_create_object():
    # Organizations
    org1 = Organization.objects.create(name="DW", description="DW Organization")
    org2 = Organization.objects.create(name="BranchCorp", description="Branch office")

    # Sites & Areas
    dw_site_a = Site.objects.create(name="DW Campus A", organization=org1)
    dw_site_b = Site.objects.create(name="DW Campus B", organization=org1)
    branch_site = Site.objects.create(name="Branch Campus", organization=org2)

    dc1 = Area.objects.create(name="Data Center 1", site=dw_site_a)
    dc2 = Area.objects.create(name="Data Center 2", site=dw_site_b)
    branch = Area.objects.create(name="Branch Office 1", site=branch_site)

    # Racks
    for area in [dc1, dc2, branch]:
        for i in range(1, 4):
            Rack.objects.create(name=f"Rack {i}", area=area)

    # Device Roles
    for role_name in ["Core Router", "Access Switch", "Firewall", "Server"]:
        DeviceRole.objects.create(name=role_name)

    # Vendors
    vendor_names = ["Cisco", "Juniper", "Arista", "Dell"]
    for v in vendor_names:
        Vendor.objects.create(name=v)

    # Device Types
    device_types_data = {
        "Cisco": ["Catalyst 9300", "ISR 4451"],
        "Juniper": ["EX4300", "SRX300"],
        "Arista": ["7050X", "7280R"],
        "Dell": ["PowerSwitch N1548", "PowerEdge R740"],
    }
    for vendor_name, models in device_types_data.items():
        vendor = Vendor.objects.get(name=vendor_name)
        for model in models:
            DeviceType.objects.create(vendor=vendor, model=model)

    all_device_types = list(DeviceType.objects.all())
    all_racks = list(Rack.objects.select_related("area__site").all())
    all_roles = list(DeviceRole.objects.all())

    for i in range(1, 11):
        dt = random.choice(all_device_types)
        rack = random.choice(all_racks)
        role = random.choice(all_roles)
        device = Device.objects.create(
            name=f"Device-{i}",
            management_ip=f"192.168.1.{i}",
            mac_address=f"00:1A:2B:3C:4D:{i:02X}",
            serial_number=f"SN{i:04}",
            inventory_number=f"INV{i:04}",
            site=rack.area.site,
            area=rack.area,
            rack=rack,
            device_type=dt,
            role=role,
            image_version="v1.0",
        )

        # Device Modules
        for idx, module_name in enumerate(["Supervisor", "Line Card"], start=1):
            DeviceModule.objects.create(
                device=device,
                name=f"{module_name} {idx}",
                serial_number=f"{device.serial_number}-MOD{idx}",
                description=f"{module_name} installed in {device.name}",
            )

        # Device Configuration (persist via domain service)
        ConfigurationPersistenceService.persist(
            device=device,
            config_text=f"Sample configuration for {device.name}",
            source="test",
        )

        # Interfaces
        statuses = [choice[0] for choice in InterfaceStatusChoices.CHOICES]
        for j in range(1, 5):
            Interface.objects.create(
                name=f"Gig0/{j}",
                device=device,
                description=f"Interface {j}",
                mac_address=f"00:1A:2B:3C:{i:02X}:{j:02X}",
                ip_address=f"10.0.{i}.{j}",
                status=random.choice(statuses),
                speed=random.choice([100, 1000, 10000]),
            )

    assert Organization.objects.count() == 2
    assert Device.objects.count() == 10
    assert Interface.objects.count() == 40
