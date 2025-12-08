import pytest
from django.test import TestCase
from django.utils import timezone
import random

# Create your tests here.
from dcim.models import (
    Organization, Site, Area, Rack, DeviceRole, Vendor, DeviceType,
    DeviceModule, Device, DeviceConfiguration, Interface
)


@pytest.mark.django_db
def test_create_object(django_db_blocker):
    with django_db_blocker.unblock():
        # -----------------------------
        # 1️⃣ Organizations
        # -----------------------------
        org1 = Organization.objects.create(name="DW", description="DW Organization")
        org2 = Organization.objects.create(name="BranchCorp", description="Branch office")
        print("Created organizations:", Organization.objects.count())

        # -----------------------------
        # 2️⃣ Sites & Areas
        # -----------------------------
        dw_site_a = Site.objects.create(name="DW Campus A", organization=org1)
        dw_site_b = Site.objects.create(name="DW Campus B", organization=org1)
        branch_site = Site.objects.create(name="Branch Campus", organization=org2)

        dc1 = Area.objects.create(name="Data Center 1", site=dw_site_a)
        dc2 = Area.objects.create(name="Data Center 2", site=dw_site_b)
        branch = Area.objects.create(name="Branch Office 1", site=branch_site)

        # -----------------------------
        # 3️⃣ Racks
        # -----------------------------
        for area in [dc1, dc2, branch]:
            for i in range(1, 4):
                Rack.objects.create(name=f"Rack {i}", area=area, u_height=42)

        # -----------------------------
        # 4️⃣ Device Roles
        # -----------------------------
        roles = ["Core Router", "Access Switch", "Firewall", "Server"]
        for r in roles:
            DeviceRole.objects.create(name=r)

        # -----------------------------
        # 5️⃣ Vendors
        # -----------------------------
        vendor_names = ["Cisco", "Juniper", "Arista", "Dell"]
        vendors = []
        for v in vendor_names:
            vendors.append(Vendor.objects.create(name=v))

        # -----------------------------
        # 7️⃣ Device Types
        # -----------------------------
        device_types_data = {
            "Cisco": ["Catalyst 9300", "ISR 4451"],
            "Juniper": ["EX4300", "SRX300"],
            "Arista": ["7050X", "7280R"],
            "Dell": ["PowerSwitch N1548", "PowerEdge R740"]
        }

        for vendor_name, models in device_types_data.items():
            vendor = Vendor.objects.get(name=vendor_name)
            for model in models:
                DeviceType.objects.create(vendor=vendor, model=model)

        # -----------------------------
        # 9️⃣ Devices
        # -----------------------------
        all_device_types = list(DeviceType.objects.all())
        all_racks = list(Rack.objects.all())
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
                vendor=dt.vendor,
                device_type=dt,
                role=role,
                image_version="v1.0",
                status=random.choice(['active', 'inactive', 'maintenance', 'unknown']),
                uptime=None
            )

            # -----------------------------
            # Device Modules
            # -----------------------------
            module_names = ["Supervisor", "Line Card"]
            for idx, module_name in enumerate(module_names, start=1):
                DeviceModule.objects.create(
                    device=device,
                    vendor=device.vendor,
                    name=f"{module_name} {idx}",
                    serial_number=f"{device.serial_number}-MOD{idx}",
                    description=f"{module_name} installed in {device.name}",
                )

            # -----------------------------
            # Device Configuration
            # -----------------------------
            DeviceConfiguration.objects.create(
                device=device,
                config_text=f"Sample configuration for {device.name}",
                updated_at=timezone.now()
            )

            # -----------------------------
            # Interfaces
            # -----------------------------
            for j in range(1, 5):
                Interface.objects.create(
                    name=f"Gig0/{j}",
                    device=device,
                    description=f"Interface {j}",
                    mac_address=f"00:1A:2B:3C:{i:02X}:{j:02X}",
                    ip_address=f"10.0.{i}.{j}",
                    status=random.choice(['up', 'down', 'disabled']),
                    speed=random.choice([100, 1000, 10000])
                )
        print("Created devices:", Device.objects.count())
        # print device details of an device
        sample_device = Device.objects.first()
        print("Sample Device:", sample_device.name, sample_device.management_ip, sample_device.device_type.model, sample_device.rack.name, sample_device.area.name)
           

    
