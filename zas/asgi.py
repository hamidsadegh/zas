import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.sessions import SessionMiddlewareStack
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zas.settings")

django_asgi_app = get_asgi_application()

try:
    from automation import ssh_routing

    websocket_urlpatterns = ssh_routing.websocket_urlpatterns
except Exception:
    websocket_urlpatterns = []

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": SessionMiddlewareStack(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)
