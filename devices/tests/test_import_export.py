import io
import pytest # pyright: ignore[reportMissingImports]
from django.utils import timezone
from django.contrib.admin.sites import AdminSite
from devices.models import Device, Organization, Vendor, DeviceType, DeviceRole, Area, Rack
from devices.admin import DeviceAdmin, export_devices_to_excel

@pytest.mark.django_db
class TestExport:

    def test_export_devices_to_excel(self, rf):
        """
        Test exporting devices to Excel from admin.
        """
        # Create related objects
        org = Organization.objects.create(name="TestOrg")
        area = Area.objects.create(name="TestArea", organization=org)
        vendor = Vendor.objects.create(name="Cisco")
        device_type = DeviceType.objects.create(model="C9300-48P", vendor=vendor)
        role = DeviceRole.objects.create(name="Access Switch")
        rack = Rack.objects.create(name="Rack A", area=area)

        # Create a device
        device = Device.objects.create(
            name="bcsw01",
            management_ip="192.168.1.1",
            organization=org,
            area=area,
            rack=rack,
            site="Berlin",
            vendor=vendor,
            device_type=device_type,
            role=role,
            status="active",
            image_version="17.06.06",
            created_at=timezone.now(),
            updated_at=timezone.now()
        )

        # Create a dummy request and queryset
        request = rf.get("/")
        queryset = Device.objects.all()

        # Admin instance
        ma = DeviceAdmin(Device, AdminSite())

        # Call the export action
        response = export_devices_to_excel(ma, request, queryset)

        # Verify response
        assert response.status_code == 200
        assert response["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert "attachment" in response["Content-Disposition"]
        content = response.content
        assert content is not None
        assert len(content) > 0  # Ensure something was written
