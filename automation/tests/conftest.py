import pytest

from dcim.models import Device, Tag, Organization, Site, Area, Vendor, DeviceType, DeviceRole
from accounts.admin_credentials import SSHCredential, SiteCredential


@pytest.fixture
def devices(db):
    organization = Organization.objects.create(name="TestOrg")
    site = Site.objects.create(name="Berlin", organization=organization)
    area = Area.objects.create(name="Berlin", site=site)
    vendor = Vendor.objects.create(name="Cisco")
    device_type = DeviceType.objects.create(vendor=vendor, model="C9300-48P")
    role = DeviceRole.objects.create(name="Access Switch")
    tag = Tag.objects.create(name="config_backup_tag")

    # Create a site credential record (if used elsewhere)
    SiteCredential.objects.create(site=site, name="sc1", type="ssh")

    # Create a device and attach the tag
    device = Device.objects.create(
        name="sw01",
        management_ip="192.168.49.128",
        site=site,
        area=area,
        device_type=device_type,
        role=role,
        status="active",
    )
    device.tags.add(tag)

    # Tests expect a QuerySet-like object with `.count()` — return a QuerySet.
    devices_qs = Device.objects.filter(site=site)

    return devices_qs


@pytest.fixture
def user(db):
    """Provide an SSHCredential instance for tests that need a user/credential."""
    organization = Organization.objects.create(name="TestOrgUser")
    site = Site.objects.create(name="UserSite", organization=organization)
    # Create and return an SSHCredential (password here is dummy for tests)
    return SSHCredential.objects.create(
        site=site,
        name="sc1-ssh",
        ssh_username="test_user",
        ssh_password="password",
    )

