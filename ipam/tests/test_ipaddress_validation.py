import pytest
from django.core.exceptions import ValidationError

from dcim.models import Organization, Device, Interface, Site, Area
from ipam.models import Prefix, IPAddress
from ipam.choices import IPAddressRoleChoices


@pytest.mark.django_db
def test_ip_outside_prefix_rejected():
    org = Organization.objects.create(name="DW")
    site = Site.objects.create(name="Campus", organization=org)

    prefix = Prefix.objects.create(cidr="10.0.0.0/24", site=site)

    ip = IPAddress(
        address="10.0.1.10",
        prefix=prefix,
    )

    with pytest.raises(ValidationError):
        ip.full_clean()


@pytest.mark.django_db
def test_two_primary_ipv4_on_interface_rejected():
    org = Organization.objects.create(name="DW")
    site = Site.objects.create(name="Campus", organization=org)
    area = Area.objects.create(name="Area 1", site=site)    

    device = Device.objects.create(name="sw1", site=site, management_ip="10.0.0.10", area=area)
    iface = Interface.objects.create(device=device, name="Gig0/1")

    prefix = Prefix.objects.create(cidr="10.0.0.0/24", site=site)

    IPAddress.objects.create(
        address="10.0.0.1",
        prefix=prefix,
        interface=iface,
        role=IPAddressRoleChoices.PRIMARY,
    )

    ip2 = IPAddress(
        address="10.0.0.2",
        prefix=prefix,
        interface=iface,
        role=IPAddressRoleChoices.PRIMARY,
    )

    with pytest.raises(ValidationError):
        ip2.full_clean()


@pytest.mark.django_db
def test_primary_ipv4_and_ipv6_allowed():
    org = Organization.objects.create(name="DW")
    site = Site.objects.create(name="Campus", organization=org)
    area = Area.objects.create(name="Area 1", site=site)    

    device = Device.objects.create(name="sw1", site=site, management_ip="10.0.0.10", area=area)
    iface = Interface.objects.create(device=device, name="Gig0/1")

    prefix4 = Prefix.objects.create(cidr="10.0.0.0/24", site=site)
    prefix6 = Prefix.objects.create(cidr="2001:db8::/64", site=site)

    IPAddress.objects.create(
        address="10.0.0.1",
        prefix=prefix4,
        interface=iface,
        role=IPAddressRoleChoices.PRIMARY,
    )

    ip6 = IPAddress(
        address="2001:db8::1",
        prefix=prefix6,
        interface=iface,
        role=IPAddressRoleChoices.PRIMARY,
    )

    ip6.full_clean()  # must NOT raise
