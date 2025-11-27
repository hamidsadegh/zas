# SITE_CHOICES
SITE_CHOICES = [
    ("Berlin", "Berlin"),
    ("Bonn", "Bonn"),
    ("Gemeinsam", "Gemeinsam"),
]

# Device choices
DEVICE_TYPE_CHOICES = [
    ("ios", "Cisco IOS Switch"),
    ("iosxe", "Cisco IOS-XE Switch"),
    ("nxos", "Cisco NX-OS Switch"),
    ("router", "Router"),
    ("firewall", "Firewall"),
    ("ap", "Access Point"),
    ("server", "Server"),
    ("other", "Other"),
]

DEVICE_STATUS_CHOICES = [
            ("active", "Active"),
            ("inactive", "Inactive"),
            ("maintenance", "Maintenance"),
            ("unknown", "Unknown"),
        ]

# VLAN usage area choices
VLAN_USAGE_CHOICES = [
        ("ACI", "ACI"),
        ("Campus", "Campus"),
        ("Management", "Management"),
        ("PostPro", "PostPro"),
        ("Autark", "Autark"),
        ("BTSU", "BTSU"),
        ("IP-Telefine", "IP-Telefone"),
        ("Frei", "Frei"),
        ("Sonstiges", "Sonstiges"),
    ]