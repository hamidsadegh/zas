from django.urls import path

from .ssh_consumer import SSHConsumer

websocket_urlpatterns = [
    path('ws/device/<uuid:device_id>/ssh/', SSHConsumer.as_asgi()),
]
