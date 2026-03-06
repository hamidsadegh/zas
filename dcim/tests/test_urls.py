from django.urls import reverse, resolve
from dcim.views.device_views import DeviceListView, device_decommission
from django.test import SimpleTestCase

class TestDeviceURLs(SimpleTestCase):
    def test_device_list_url_resolves(self):
        url = reverse('device_list')
        resolved = resolve(url)
        # Check the view class
        self.assertEqual(resolved.func.view_class, DeviceListView)

    def test_device_decommission_url_resolves(self):
        url = reverse("device_decommission", kwargs={"pk": "123e4567-e89b-12d3-a456-426614174000"})
        resolved = resolve(url)
        self.assertEqual(resolved.func, device_decommission)
