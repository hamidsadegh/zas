from django.urls import path

from .views import DeviceTopologyNeighborsView

urlpatterns = [
    path(
        "device/<uuid:device_id>/neighbors/",
        DeviceTopologyNeighborsView.as_view(),
        name="topology-device-neighbors",
    ),
]
