from django.urls import path
from . import views
from .views import debug_session

urlpatterns = [
    path("", views.home, name="dashboard"),
    # TEMP URL for testing
    path("debug-session/", debug_session, name="debug-session"),
    # TEMP END
]
