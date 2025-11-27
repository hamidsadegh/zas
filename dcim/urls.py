# /code/devices/urls.py

from django.urls import path
from .views import device_views
from .views.device_views import DeviceListView, DeviceDetailView, racks_by_area

urlpatterns = [
    # Dashboard / home
    path('', device_views.home, name='home'),

    # Devices (HTML views)
    # path('devices/', views.device_list, name='device_list'),
    # path('devices/<int:pk>/', views.device_detail, name='device_detail'),
    path('', DeviceListView.as_view(), name='device_list'),
    path('<int:pk>/', DeviceDetailView.as_view(), name='device_detail'),

    # Areas
    path('areas/', device_views.area_list, name='area_list'),
    path('areas/<int:pk>/', device_views.area_detail, name='area_detail'),
    path('areas/<int:area_id>/devices/', device_views.devices_by_area, name='devices_by_area'),

    # Racks
    path('racks/', device_views.rack_list, name='rack_list'),

    # ⭐ AJAX endpoint (required for filtered Rack dropdown)
    path('ajax/racks/', device_views.racks_by_area, name='racks_by_area'),
]