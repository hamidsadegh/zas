from django.db import models


class PrefixStatusChoices(models.TextChoices):
    ACTIVE = "active", "Active"
    RESERVED = "reserved", "Reserved"
    DEPRECATED = "deprecated", "Deprecated"


class PrefixRoleChoices(models.TextChoices):
    USER = "user", "User"
    MGMT = "mgmt", "Management"
    LOOPBACK = "loopback", "Loopback"
    TRANSIT = "transit", "Transit"
    INFRA = "infra", "Infrastructure"


class IPAddressStatusChoices(models.TextChoices):
    ACTIVE = "active", "Active"
    DHCP = "dhcp", "DHCP"
    RESERVED = "reserved", "Reserved"
    DEPRECATED = "deprecated", "Deprecated"


class IPAddressRoleChoices(models.TextChoices):
    PRIMARY = "primary", "Primary"
    SECONDARY = "secondary", "Secondary"
    VIP = "vip", "VIP"
    LOOPBACK = "loopback", "Loopback"
