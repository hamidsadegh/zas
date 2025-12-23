import pytest

from dcim.models import Site, Organization
from ipam.models import Prefix, IPAddress
from ipam.services.ip_allocation_service import IPAllocationService


@pytest.mark.django_db
def test_next_available_ip():
    org = Organization.objects.create(name="DW")
    site = Site.objects.create(name="Campus", organization=org)

    prefix = Prefix.objects.create(cidr="10.0.0.0/30", site=site)

    ip1 = IPAllocationService.next_available_ip(prefix)
    IPAddress.objects.create(address=ip1, prefix=prefix)

    ip2 = IPAllocationService.next_available_ip(prefix)

    assert ip1 != ip2
