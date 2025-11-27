from django.urls import reverse, resolve
from dcim.views.device_views import DeviceListView
from django.test import SimpleTestCase

class TestDeviceURLs(SimpleTestCase):
    def test_device_list_url_resolves(self):
        url = reverse('device_list')
        resolved = resolve(url)
        # Check the view class
        self.assertEqual(resolved.func.view_class, DeviceListView)
