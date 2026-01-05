import pytest
from django.core.exceptions import ValidationError

from ipam.models import Prefix, VRF
from ipam.services.prefix_validation_service import PrefixValidationService
from dcim.models import Site, Organization


@pytest.mark.django_db
class TestPrefixValidation:
    def test_overlapping_prefix_rejected(self):
        """
        Two overlapping prefixes in the same site + VRF are not allowed
        unless hierarchical.
        """
        # Organizations
        org1= Organization.objects.create(name="DW", description="DW Organization")

        # Sites
        dw_site_a= Site.objects.create(name="DW Campus A", organization=org1)

        Prefix.objects.create(
            cidr="10.0.0.0/24",
            site=dw_site_a,
        )

        overlapping= Prefix.objects.create(
            cidr="10.0.0.128/25",
            site=dw_site_a,
        )

        with pytest.raises(ValidationError):
            PrefixValidationService(overlapping).validate()

    def test_hierarchical_prefix_allowed(self):
        """
        A child prefix is allowed if it is properly nested
        and parent is explicitly set.
        """
        # Organizations
        org1= Organization.objects.create(name="DW", description="DW Organization")

        # Sites
        dw_site_a= Site.objects.create(name="DW Campus A", organization=org1)

        parent= Prefix.objects.create(
            cidr="10.0.0.0/24",
            site=dw_site_a,
        )

        child= Prefix.objects.create(
            cidr="10.0.0.128/25",
            site=dw_site_a,
            parent=parent,
        )

        # Should not raise
        PrefixValidationService(child).validate()

    def test_prefix_wrong_vrf_rejected(self):
        """
        Prefix cannot belong to a VRF from a different site.
        """
        # Organizations
        org1= Organization.objects.create(name="DW", description="DW Organization")

        # Sites 
        dw_site_a= Site.objects.create(name="DW Campus A", organization=org1)
        dw_site_b= Site.objects.create(name="DW Campus B", organization=org1)


        vrf= VRF.objects.create(
            name="VRF-A",
            site=dw_site_a,
        )

        prefix= Prefix.objects.create(
            cidr="10.1.0.0/24",
            site=dw_site_b,
            vrf=vrf,
        )

        with pytest.raises(ValidationError):
            PrefixValidationService(prefix).validate()

    def test_duplicate_prefix_same_site_rejected(self):
        """
        Same prefix CIDR cannot exist twice in the same site / VRF.
        """
        org = Organization.objects.create(name="DW")
        site = Site.objects.create(name="DW Campus A", organization=org)

        # First prefix (exists in DB)
        Prefix.objects.create(
            cidr="192.168.0.0/24",
            site=site,
        )

        # Duplicate candidate (NOT saved)
        duplicate = Prefix(
            cidr="192.168.0.0/24",
            site=site,
        )

        with pytest.raises(ValidationError):
            duplicate.full_clean()

