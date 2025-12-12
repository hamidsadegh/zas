import os
import sys
import random

import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zas.settings.base")
django.setup()

from django.utils import timezone  # noqa: E402

from dcim.models import (  # noqa: E402
    Organization,
    Site,
    Area,
    Rack,
    DeviceRole,
    Vendor,
    DeviceType,
    Device,
    DeviceConfiguration,
    Interface,
)


# Organizations
org, created = Organization.objects.get_or_create(
    name="DW",
    defaults={"description": "Deutsche Welle"}
)
print(f"Organization '{org.name}' {'created' if created else 'already exists'}.")

# Site creation
sites = {["Berlin", "Voltastraße 6, 13355 Berlin"], ["Bonn", "Kurt-Schumacher-Straße 3, 53113 Bonn"], ["Standortübergreifend", ""]}
for site_name, site_address in sites:
    site, created = Site.objects.get_or_create(
        name=site_name,
        organization=org,
        defaults={"address": site_address}
    )
print(f"Site '{site.name}' {'created' if created else 'already exists'}.")

# 2️⃣ Create Areas for Berlin and Bonn
def create_area_hierarchy(site, hierarchy_list):
    """Erstellt oder findet eine verschachtelte Area-Hierarchie."""
    parent = None
    for name in hierarchy_list:
        area, _ = Area.objects.get_or_create(
            name=name,
            parent=parent,
            site=site
        )
        parent = area
    return parent


# Hilfsfunktion: Zahlenspannen in Textnamen umwandeln
def floors(start, end, suffix):
    return [f"{i}{suffix}" for i in range(start, end + 1)]

def houses(prefix, start, end):
    return [f"{prefix} {i}" for i in range(start, end + 1)]


# Hierarchien definieren (automatisch erweitert)
hierarchy_berlin = []

# # Berlin Altbau
hierarchy_berlin.append(["Berlin"])
hierarchy_berlin.append(["Berlin", "BPH"])
hierarchy_berlin.append(["Berlin", "Altbau"])
hierarchy_berlin.append(["Berlin", "Altbau", "UG"])
hierarchy_berlin.append(["Berlin", "Altbau", "EG"])
hierarchy_berlin.append(["Berlin", "Altbau", "TSU"])
hierarchy_berlin.append(["Berlin", "Altbau", "EG", "A023A"])
hierarchy_berlin.append(["Berlin", "Altbau", "EG", "A027"])

for floor in floors("OG", 1, 5):
    hierarchy_berlin.append(["Altbau", floor])

hierarchy_berlin.append(["Berlin", "Altbau", "1OG", "A0198"])
hierarchy_berlin.append(["Berlin", "Altbau", "1OG", "A120A"])
hierarchy_berlin.append(["Berlin", "Altbau", "1OG", "A179D"])
hierarchy_berlin.append(["Berlin", "Altbau", "1OG", "A191B"])
hierarchy_berlin.append(["Berlin", "Altbau", "3OG", "A307A"])
hierarchy_berlin.append(["Berlin", "Altbau", "3OG", "A324"])
hierarchy_berlin.append(["Berlin", "Altbau", "3OG", "A327"])
hierarchy_berlin.append(["Berlin", "Altbau", "3OG", "A332"])
hierarchy_berlin.append(["Berlin", "Altbau", "3OG", "A346"])
hierarchy_berlin.append(["Berlin", "Altbau", "3OG", "A360"])
hierarchy_berlin.append(["Berlin", "Altbau", "3OG", "A383"])
hierarchy_berlin.append(["Berlin", "Altbau", "3OG", "A384"])
hierarchy_berlin.append(["Berlin", "Altbau", "4OG", "A424"])
hierarchy_berlin.append(["Berlin", "Altbau", "4OG", "A431"])
hierarchy_berlin.append(["Berlin", "Altbau", "4OG", "A476A"])
hierarchy_berlin.append(["Berlin", "Altbau", "4OG", "A406A"])
hierarchy_berlin.append(["Berlin", "Altbau", "4OG", "A406A"])
hierarchy_berlin.append(["Berlin", "Altbau", "5OG", "A570"])
hierarchy_berlin.append(["Berlin", "Altbau", "5OG", "A574"])
hierarchy_berlin.append(["Berlin", "Altbau", "5OG", "A575"])
hierarchy_berlin.append(["Berlin", "Altbau", "5OG", "A576"])
hierarchy_berlin.append(["Berlin", "Altbau", "5OG", "A580"])
hierarchy_berlin.append(["Berlin", "Altbau", "5OG", "A587"])

# Berlin Neubau
hierarchy_berlin.append(["Berlin", "Neubau"])
hierarchy_berlin.append(["Berlin", "Neubau", "1OG"])
hierarchy_berlin.append(["Berlin", "Neubau", "1OG", "N1FLEX1"])
hierarchy_berlin.append(["Berlin", "Neubau", "11OG"])
hierarchy_berlin.append(["Berlin", "Neubau", "TG"])
hierarchy_berlin.append(["Berlin", "Neubau", "EG"])

for floor in floors(3, 4, "OG"):
    hierarchy_berlin.append(["Neubau", floor])

for floor in floors(6, 7, "OG"):
    hierarchy_berlin.append(["Neubau", floor])

hierarchy_berlin.append(["Berlin", "Neubau", "3OG", "N316A"])
hierarchy_berlin.append(["Berlin", "Neubau", "4OG", "N403B"])
hierarchy_berlin.append(["Berlin", "Neubau", "4OG", "N414A"])
hierarchy_berlin.append(["Berlin", "Neubau", "6OG", "N615A"])
hierarchy_berlin.append(["Berlin", "Neubau", "7OG", "N710A"])
hierarchy_berlin.append(["Berlin", "Neubau", "9OG", "N908A"])
hierarchy_berlin.append(["Berlin", "Neubau", "11OG", "N1106"])
hierarchy_berlin.append(["Berlin", "Neubau", "11OG", "N1107"])
hierarchy_berlin.append(["Berlin", "Neubau", "11OG", "N1109"])
hierarchy_berlin.append(["Berlin", "Neubau", "11OG", "N1110"])

#  Hierarchy Berlin erstellen
s = Site.objects.get(name="Berlin")
for h in hierarchy_berlin:
    create_area_hierarchy(s, h)


hierarchy_bonn = []
hierarchy_bonn.append(["Bonn"])
# Bonn Haus 1–9
for haus in houses("Haus", 1, 9):
    hierarchy_bonn.append([haus])

#  Hierarchy Bonn erstellen
s = Site.objects.get(name="Bonn")
for h in hierarchy_bonn:
    create_area_hierarchy(s, h)

print("All area hierarchies created.")

# -----------------------------
# Racks
# -----------------------------
a = Area.objects.get(name="0198")
Rack.objects.get_or_create(name=f"RackA1", area=a)
Rack.objects.get_or_create(name=f"RackB3", area=a)
Rack.objects.get_or_create(name=f"RackB6", area=a)
Rack.objects.get_or_create(name=f"RackB9", area=a)
Rack.objects.get_or_create(name=f"RackC3", area=a)
Rack.objects.get_or_create(name=f"RackC6", area=a)
Rack.objects.get_or_create(name=f"RackC9", area=a)
a = Area.objects.get(name="A324")
Rack.objects.get_or_create(name=f"Rack37", area=a)
Rack.objects.get_or_create(name=f"Rack43", area=a)
Rack.objects.get_or_create(name=f"Rack44", area=a)
Rack.objects.get_or_create(name=f"Rack46", area=a)
Rack.objects.get_or_create(name=f"Rack63", area=a)
Rack.objects.get_or_create(name=f"Rack106", area=a)
Rack.objects.get_or_create(name=f"Rack108", area=a)
Rack.objects.get_or_create(name=f"Rack109", area=a)
Rack.objects.get_or_create(name=f"Rack116", area=a)
Rack.objects.get_or_create(name=f"Rack118", area=a)
Rack.objects.get_or_create(name=f"Rack125", area=a)
a = Area.objects.get(name="A384")
Rack.objects.get_or_create(name=f"Rack00", area=a)
Rack.objects.get_or_create(name=f"Rack03", area=a)
Rack.objects.get_or_create(name=f"Rack11", area=a)
a = Area.objects.get(name="A587")
Rack.objects.get_or_create(name=f"RackB2", area=a)
Rack.objects.get_or_create(name=f"RackB4", area=a)
Rack.objects.get_or_create(name=f"RackC6", area=a)
Rack.objects.get_or_create(name=f"RackC7", area=a)
a = Area.objects.get(name="A0198")
Rack.objects.get_or_create(name=f"RackB3", area=a)
Rack.objects.get_or_create(name=f"RackB6", area=a)
Rack.objects.get_or_create(name=f"RackC3", area=a)
Rack.objects.get_or_create(name=f"RackC6", area=a)
Rack.objects.get_or_create(name=f"RackC9", area=a)
print("All racks created.")

# Device Roles
roles = ["Core Switch", "Access Switch", "Distribution Switch" , "Router", "Firewall", "Server"]
for r in roles:
    DeviceRole.objects.get_or_create(name=r)
print("All device roles created.")

# Vendors
vendor_data = [
    ["Cisco", "https://www.cisco.com/"],
    ["Juniper", "https://www.juniper.net/"],
    ["Arista", "https://www.arista.com/"],
    ["Dell", "https://www.dell.com/"]
]
vendors = []
for name, web in vendor_data:
    vendors.append(Vendor.objects.get_or_create(name=name, website=web)[0])
print("All vendors created.")

# Device Types
device_types_data = [
    # ---------- IOS-XE ----------
    ["C9300-48P", "iosxe", "Cisco Catalyst 9300 Series Switches"],
    ["C9606R", "iosxe", "Cisco Catalyst 9600 Series Routers"],
    ["C9600-LC-24C", "iosxe", "Cisco Catalyst 9600 Series Switches"],
    ["C9500-48Y4C", "iosxe", "Cisco Catalyst 9500 Series Switches"],
    ["C9200L-48T-4X", "iosxe", "Cisco Catalyst 9200 Series Switches"],
    ["C9300-48T", "iosxe", "Cisco Catalyst 9300 Series Switches"],
    ["WS-C3850-48P", "iosxe", "Cisco Catalyst 3850 Series Switches"],
    ["ASR-920-24SZ-IM", "iosxe", "Cisco ASR 920 Routers"],
    ["WS-C3750X-24", "iosxe", "Cisco Catalyst 3750-X Series Switches"],
    ["C9500-32QC", "iosxe", "Cisco Catalyst 9500 Series Switches"],
    ["C9300-24T", "iosxe", "Cisco Catalyst 9300 Series Switches"],
    ["C9200CX-12P-2X2G", "iosxe", "Cisco Catalyst 9200-CX Series Switches"],
    ["C9300-48UB", "iosxe", "Cisco Catalyst 9300 Series Switches"],

    # ---------- NX-OS ----------
    ["C93108TC-FX", "nxos", "Cisco Nexus 9000 Series Switches"],
    ["C93180YC-FX", "nxos", "Cisco Nexus 9000 Series Switches"],
    ["C9336C-FX2", "nxos", "Cisco Nexus 9000 Series Switches"],
    ["N9K-C93600CD-GX", "nxos", "Cisco Nexus 9300 Switches"],
    ["C93180YC-EX", "nxos", "Cisco Nexus 9300 Switches"],

    # ---------- IOS ----------
    ["WS-C2960XR-48LPD-I", "ios", "Cisco Catalyst 2960-X Series Switches"],
    ["WS-C2960-24TC-L", "ios", "Cisco Catalyst 2960 Series Switches"],
    ["WS-C4948E", "ios", "Cisco Catalyst 4948 Switches"],
    ["WS-C2960XR-48TD-I", "ios", "Cisco Catalyst 2960-X Series Switches"],
    ["WS-C3560CX-12PC-S", "ios", "Cisco Catalyst 3560-CX Series Switches"],
    ["WS-C2960XR-48LPS-I", "ios", "Cisco Catalyst 2960-X Series Switches"],
    ["C7009", "ios", "Cisco 7000 Series Chassis"],
    ["WS-C2960G-24TC-L", "ios", "Cisco Catalyst 2960-G Series Switches"],
]
for model, platform, description in device_types_data:
    vendor = Vendor.objects.get(name="Cisco")
    DeviceType.objects.get_or_create(
        vendor=vendor,
        model=model,
        defaults={"description": description},
    )

# # -----------------------------
# # Module Types
# # -----------------------------
# module_types_data = {
#     "Cisco": ["Module A", "Module B"],
#     "Juniper": ["Module J1", "Module J2"]
# }

# for vendor_name, modules in module_types_data.items():
#     vendor = Vendor.objects.get(name=vendor_name)
#     for m in modules:
#         DeviceModule.objects.create(vendor=vendor, name=m)

# -----------------------------
# Devices
# -----------------------------
from dcim.choices import InterfaceStatusChoices  # noqa: E402

all_device_types = list(DeviceType.objects.all())
all_racks = [r for r in Rack.objects.select_related("area__site").all() if r.area and r.area.site_id]
all_roles = list(DeviceRole.objects.all())

for i in range(1, 11):
    if not all_device_types or not all_racks or not all_roles:
        break
    dt = random.choice(all_device_types)
    rack = random.choice(all_racks)
    role = random.choice(all_roles)
    device = Device.objects.create(
        name=f"Device-{i}",
        management_ip=f"192.168.1.{i}",
        mac_address=f"00:1A:2B:3C:4D:{i:02X}",
        serial_number=f"SN{i:04}",
        inventory_number=f"INV{i:04}",
        area=rack.area,
        rack=rack,
        site=rack.area.site,
        vendor=dt.vendor,
        device_type=dt,
        role=role,
        image_version="v1.0",
    )

    # Device Configuration
    DeviceConfiguration.objects.create(
        device=device,
        config_text=f"Sample configuration for {device.name}",
        backup_time=timezone.now(),
        success=True,
    )

    # Interfaces
    for j in range(1, 5):
        Interface.objects.create(
            name=f"Gig0/{j}",
            device=device,
            description=f"Interface {j}",
            mac_address=f"00:1A:2B:3C:{i:02X}:{j:02X}",
            ip_address=f"10.0.{i}.{j}",
            status=random.choice(
                [choice[0] for choice in InterfaceStatusChoices.CHOICES]
            ),
            speed=random.choice([100, 1000, 10000]),
        )
