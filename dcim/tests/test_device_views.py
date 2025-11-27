from django.test import TestCase, Client
from django.contrib.auth.models import User
from dcim.models import Device, Organization

class TestDeviceViews(TestCase):
    def setUp(self):
        # Create a user and log them in
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = Client()
        self.client.login(username='testuser', password='testpass')

        # Create minimal objects for Device
        self.org = Organization.objects.create(name="TestOrg")
        self.device = Device.objects.create(
            name="Device01",
            management_ip="192.168.1.1",
            organization=self.org,
        )

    def test_device_list_view(self):
        response = self.client.get('/devices/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Device01")
