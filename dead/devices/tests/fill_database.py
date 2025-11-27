import os
import django
import sys

sys.path.append("/opt/code/zas")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zas_project.settings")
django.setup()
from django.utils import timezone
import random
from devices.models import (
    Organization, Area, Rack, DeviceRole, Vendor, DeviceType,
    ModuleType, Device, DeviceConfiguration, Interface
)


# Organizations
org, created = Organization.objects.get_or_create(
    name="DW",
    defaults={"description": "Deutsche Welle"}
)
print(f"Organization '{org.name}' {'created' if created else 'already exists'}.")
# 2️⃣ Create Arias for Berlin and Bonn 
def create_area_hierarchy(org, hierarchy_list):
    """Erstellt oder findet eine verschachtelte Area-Hierarchie."""
    parent = None
    for name in hierarchy_list:
        area, _ = Area.objects.get_or_create(
            name=name,
            parent=parent,
            organization=org
        )
        parent = area
    return parent


# Hilfsfunktion: Zahlenspannen in Textnamen umwandeln
def floors(prefix, start, end, suffix="OG"):
    return [f"{i}{suffix}" for i in range(start, end + 1)]

def houses(prefix, start, end):
    return [f"Haus {i}" for i in range(start, end + 1)]


# Hierarchien definieren (automatisch erweitert)
hierarchies = []

# Berlin Altbau 1–6OG
for floor in floors("OG", 1, 6):
    hierarchies.append(["Global", "Europe", "Berlin", "Altbau", floor])
hierarchies.append(["Global", "Europe", "Bruessel"])
hierarchies.append(["Global", "Europe", "Berlin", "BPH"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "UG"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "EG"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "TSU"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "EG", "A023A"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "EG", "A027"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "EG", "A0198"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "1OG", "A120A"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "1OG", "A179D"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "1OG", "A191B"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "3OG", "A307A"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "3OG", "A324"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "3OG", "A327"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "3OG", "A332"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "3OG", "A346"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "3OG", "A360"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "3OG", "A383"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "3OG", "A384"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "4OG", "A424"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "4OG", "A431"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "4OG", "A476A"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "4OG", "A406A"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "4OG", "A406A"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "5OG", "A570"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "5OG", "A574"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "5OG", "A575"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "5OG", "A576"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "5OG", "A580"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "5OG", "A587"])
hierarchies.append(["Global", "Europe", "Berlin", "Altbau", "6OG", "A687"])
# Berlin Neubau 3–11OG
for floor in floors("OG", 3, 4):
    hierarchies.append(["Global", "Europe", "Berlin", "Neubau", floor])
for floor in floors("OG", 6, 7):
    hierarchies.append(["Global", "Europe", "Berlin", "Neubau", floor])
hierarchies.append(["Global", "Europe", "Berlin", "Neubau", "1OG"])
hierarchies.append(["Global", "Europe", "Berlin", "Neubau", "1OG", "N1FLEX1"])
hierarchies.append(["Global", "Europe", "Berlin", "Neubau", "11OG"])
hierarchies.append(["Global", "Europe", "Berlin", "Neubau", "TG"])
hierarchies.append(["Global", "Europe", "Berlin", "Neubau", "EG"])
hierarchies.append(["Global", "Europe", "Berlin", "Neubau", "N3OG", "N316A"])
hierarchies.append(["Global", "Europe", "Berlin", "Neubau", "N4OG", "N403B"])
hierarchies.append(["Global", "Europe", "Berlin", "Neubau", "N4OG", "N414A"])
hierarchies.append(["Global", "Europe", "Berlin", "Neubau", "N6OG", "N615A"])
hierarchies.append(["Global", "Europe", "Berlin", "Neubau", "N7OG", "N710A"])
hierarchies.append(["Global", "Europe", "Berlin", "Neubau", "N9OG", "N908A"])
hierarchies.append(["Global", "Europe", "Berlin", "Neubau", "N11OG", "N1106"])
hierarchies.append(["Global", "Europe", "Berlin", "Neubau", "N11OG", "N1107"])
hierarchies.append(["Global", "Europe", "Berlin", "Neubau", "N11OG", "N1109"])
hierarchies.append(["Global", "Europe", "Berlin", "Neubau", "N11OG", "N1110"])



# Bonn Haus 1–9
for haus in houses("Haus", 1, 9):
    hierarchies.append(["Global", "Europe", "Bonn", haus])


# Alle Hierarchien erstellen
for h in hierarchies:
    create_area_hierarchy(org, h)

print("All area hierarchies created.")

# -----------------------------
# Racks
# -----------------------------
a = Area.objects.get(name="A324")
Rack.objects.get_or_create(name=f"Rack37", area=a, height=42)
Rack.objects.get_or_create(name=f"Rack43", area=a, height=42)
Rack.objects.get_or_create(name=f"Rack44", area=a, height=42)
Rack.objects.get_or_create(name=f"Rack46", area=a, height=42)
Rack.objects.get_or_create(name=f"Rack63", area=a, height=42)
Rack.objects.get_or_create(name=f"Rack106", area=a, height=42)
Rack.objects.get_or_create(name=f"Rack108", area=a, height=42)
Rack.objects.get_or_create(name=f"Rack109", area=a, height=42)
Rack.objects.get_or_create(name=f"Rack116", area=a, height=42)
Rack.objects.get_or_create(name=f"Rack118", area=a, height=42)
Rack.objects.get_or_create(name=f"Rack125", area=a, height=42)
a = Area.objects.get(name="A384")
Rack.objects.get_or_create(name=f"Rack00", area=a, height=42)
Rack.objects.get_or_create(name=f"Rack03", area=a, height=42)
Rack.objects.get_or_create(name=f"Rack11", area=a, height=42)
a = Area.objects.get(name="A587")
Rack.objects.get_or_create(name=f"RackB2", area=a, height=42)
Rack.objects.get_or_create(name=f"RackB4", area=a, height=42)
Rack.objects.get_or_create(name=f"RackC6", area=a, height=42)
Rack.objects.get_or_create(name=f"RackC7", area=a, height=42)
a = Area.objects.get(name="A0198")
Rack.objects.get_or_create(name=f"RackB3", area=a, height=42)
Rack.objects.get_or_create(name=f"RackB6", area=a, height=42)
Rack.objects.get_or_create(name=f"RackC3", area=a, height=42)
Rack.objects.get_or_create(name=f"RackC6", area=a, height=42)
Rack.objects.get_or_create(name=f"RackC9", area=a, height=42)
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
for model, category, discription in device_types_data:
    vendor = Vendor.objects.get(name="Cisco")
    DeviceType.objects.get_or_create(vendor=vendor, model=model, category=category, description=discription)

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
#         ModuleType.objects.create(vendor=vendor, name=m)

# # -----------------------------
# # Devices
# # -----------------------------
# all_device_types = list(DeviceType.objects.all())
# all_racks = list(Rack.objects.all())
# all_roles = list(DeviceRole.objects.all())
# all_orgs = list(Organization.objects.all())

# for i in range(1, 11):
#     dt = random.choice(all_device_types)
#     rack = random.choice(all_racks)
#     role = random.choice(all_roles)
#     org = random.choice(all_orgs)
#     device = Device.objects.create(
#         name=f"Device-{i}",
#         management_ip=f"192.168.1.{i}",
#         mac_address=f"00:1A:2B:3C:4D:{i:02X}",
#         serial_number=f"SN{i:04}",
#         inventory_number=f"INV{i:04}",
#         organization=org,
#         area=rack.area,
#         vendor=dt.vendor,
#         device_type=dt,
#         role=role,
#         image_version="v1.0",
#         status=random.choice(['active', 'inactive', 'maintenance', 'unknown']),
#         uptime=None
#     )

#     # -----------------------------
#     # Device Configuration
#     # -----------------------------
#     DeviceConfiguration.objects.create(
#         device=device,
#         config_text=f"Sample configuration for {device.name}",
#         last_updated=timezone.now()
#     )

#     # -----------------------------
#     # Interfaces
#     # -----------------------------
#     for j in range(1, 5):
#         Interface.objects.create(
#             name=f"Gig0/{j}",
#             device=device,
#             description=f"Interface {j}",
#             mac_address=f"00:1A:2B:3C:{i:02X}:{j:02X}",
#             ip_address=f"10.0.{i}.{j}",
#             status=random.choice(['up', 'down', 'disabled']),
#             speed=random.choice([100, 1000, 10000])
#         )
