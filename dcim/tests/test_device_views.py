from unittest.mock import patch

from django.test import TestCase, Client
from django.contrib.auth.models import User
from asset.models import InventoryItem
from dcim.models import (
    Area,
    Device,
    DeviceConfiguration,
    DeviceModule,
    Organization,
    Site,
)

class TestDeviceViews(TestCase):
    def setUp(self):
        # Create a user and log them in
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = Client()
        self.client.login(username='testuser', password='testpass')

        # Create minimal objects for Device
        self.org = Organization.objects.create(name="TestOrg")
        site = Site.objects.create(name="Site A", organization=self.org)
        area = Area.objects.create(name="Data Center 1", site=site)
        self.device = Device.objects.create(
            name="Device01",
            management_ip="192.168.1.1",
            site=site,
            area=area,
        )

    def test_device_list_view(self):
        response = self.client.get('/devices/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Device01")

    def test_device_decommission_delete_permanently(self):
        response = self.client.post(
            f"/devices/{self.device.id}/decommission/",
            {"stage": "confirm", "decision": "delete"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Device.objects.filter(id=self.device.id).exists())

    def test_device_decommission_move_to_storage(self):
        module = DeviceModule.objects.create(
            device=self.device,
            name="Uplink Module 1",
            description="8x10G Uplink Module",
            serial_number="FCH1234ABCD",
        )

        response = self.client.post(
            f"/devices/{self.device.id}/decommission/",
            {"stage": "confirm", "decision": "storage"},
        )
        self.assertEqual(response.status_code, 200)

        payload = {
            "stage": "storage",
            "form-TOTAL_FORMS": "2",
            "form-INITIAL_FORMS": "2",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-source_key": f"device:{self.device.id}",
            "form-0-action": "store",
            "form-0-item_type": InventoryItem.ItemType.DEVICE,
            "form-0-designation": "Switch",
            "form-0-inventory_number": "INV-1000",
            "form-0-area": str(self.device.area_id),
            "form-0-vendor": "",
            "form-0-status": InventoryItem.Status.IN_STOCK,
            "form-0-comment": "",
            "form-1-source_key": f"module:{module.id}",
            "form-1-action": "store",
            "form-1-item_type": InventoryItem.ItemType.MODULE,
            "form-1-designation": "Uplink Module",
            "form-1-inventory_number": "INV-1001",
            "form-1-area": str(self.device.area_id),
            "form-1-vendor": "",
            "form-1-status": InventoryItem.Status.IN_STOCK,
            "form-1-comment": "",
        }
        response = self.client.post(
            f"/devices/{self.device.id}/decommission/",
            payload,
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Device.objects.filter(id=self.device.id).exists())
        self.assertEqual(InventoryItem.objects.count(), 2)

    @patch("dcim.views.device_views._run_post_replacement_sync")
    @patch("dcim.views.device_views._push_config_to_replacement_device")
    def test_device_decommission_replace_device(
        self,
        mock_push_config,
        mock_run_sync,
    ):
        mock_push_config.return_value = (True, "")
        mock_run_sync.return_value = {"success": True}

        DeviceConfiguration.objects.create(
            device=self.device,
            config_text="interface vlan 10\n ip address 10.0.10.1 255.255.255.0",
            config_hash="a" * 64,
            source="import",
            success=True,
        )

        response = self.client.post(
            f"/devices/{self.device.id}/decommission/",
            {
                "stage": "replace",
                "name": "Device01-Repl",
                "management_ip": "192.168.1.2",
                "area": str(self.device.area_id),
                "rack": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Device.objects.filter(id=self.device.id).exists())
        self.assertTrue(Device.objects.filter(name="Device01-Repl").exists())
        mock_push_config.assert_called_once()
        mock_run_sync.assert_called_once()
