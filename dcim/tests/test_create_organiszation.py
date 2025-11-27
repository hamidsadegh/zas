import pytest
from dcim.models import Organization

@pytest.mark.django_db
def test_create_object(django_db_blocker):
    with django_db_blocker.unblock():
        org1 = Organization.objects.create(name="DW", description="DW Organization")
        org2 = Organization.objects.create(name="BranchCorp", description="Branch office")

        print("Created organizations:", Organization.objects.count())