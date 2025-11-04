from devices.models import (
    Organization, Area, Rack, DeviceRole, Vendor, Platform, DeviceType,
    ModuleType, Device, DeviceConfiguration, Interface
)
from django.utils import timezone
import random

# -----------------------------
# 1️⃣ Organizations
# -----------------------------
org1 = Organization.objects.create(name="GlobalTech", description="Main organization")
org2 = Organization.objects.create(name="BranchCorp", description="Branch office")

# -----------------------------
# 2️⃣ Areas
# -----------------------------
dc1 = Area.objects.create(name="Data Center 1", organization=org1)
dc2 = Area.objects.create(name="Data Center 2", organization=org1)
branch = Area.objects.create(name="Branch Office 1", organization=org2)

# -----------------------------
# 3️⃣ Racks
# -----------------------------
for area in [dc1, dc2, branch]:
    for i in range(1, 4):
        Rack.objects.create(name=f"Rack {i}", site=area, height=42)

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
# 6️⃣ Platforms
# -----------------------------
platforms_data = [
    ("Cisco", "IOS"), ("Cisco", "NX-OS"),
    ("Juniper", "Junos"), ("Arista", "EOS"), ("Dell", "ESXi")
]

for vendor_name, platform_name in platforms_data:
    vendor = Vendor.objects.get(name=vendor_name)
    Platform.objects.create(vendor=vendor, name=platform_name)

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
        DeviceType.objects.create(vendor=vendor, model=model, category="other")

# -----------------------------
# 8️⃣ Module Types
# -----------------------------
module_types_data = {
    "Cisco": ["Module A", "Module B"],
    "Juniper": ["Module J1", "Module J2"]
}

for vendor_name, modules in module_types_data.items():
    vendor = Vendor.objects.get(name=vendor_name)
    for m in modules:
        ModuleType.objects.create(vendor=vendor, name=m)

# -----------------------------
# 9️⃣ Devices
# -----------------------------
all_device_types = list(DeviceType.objects.all())
all_platforms = list(Platform.objects.all())
all_racks = list(Rack.objects.all())
all_roles = list(DeviceRole.objects.all())
all_orgs = list(Organization.objects.all())

for i in range(1, 11):
    dt = random.choice(all_device_types)
    platform = random.choice(all_platforms)
    rack = random.choice(all_racks)
    role = random.choice(all_roles)
    org = random.choice(all_orgs)
    device = Device.objects.create(
        name=f"Device-{i}",
        management_ip=f"192.168.1.{i}",
        mac_address=f"00:1A:2B:3C:4D:{i:02X}",
        serial_number=f"SN{i:04}",
        inventory_number=f"INV{i:04}",
        organization=org,
        area=rack.site,
        vendor=dt.vendor,
        device_type=dt,
        platform=platform,
        role=role,
        image_version="v1.0",
        status=random.choice(['active', 'inactive', 'maintenance', 'unknown']),
        uptime=None
    )

    # -----------------------------
    # 10️⃣ Device Configuration
    # -----------------------------
    DeviceConfiguration.objects.create(
        device=device,
        config_text=f"Sample configuration for {device.name}",
        last_updated=timezone.now()
    )

    # -----------------------------
    # 11️⃣ Interfaces
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
