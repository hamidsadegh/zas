from django.urls import path
from network.views.discovery import (
    discovery_dashboard,
    discovery_candidates,
    discovery_candidates_action,
    discovery_candidate_detail,
    create_device_from_candidate,
    resolve_discovery_mismatch,
)

app_name = "network"

urlpatterns = [
    path("discovery/", discovery_dashboard, name="discovery_dashboard"),
    path("discovery/candidates/", discovery_candidates, name="discovery_candidates"),
    path(
        "discovery/candidates/<uuid:pk>/create-device/",
        create_device_from_candidate,
        name="create_device_from_candidate",
    ),
    path(
        "discovery/candidates/<uuid:pk>/resolve/",
        resolve_discovery_mismatch,
        name="resolve_discovery_mismatch",
    ),
    path(
        "discovery/candidates/<uuid:pk>/",
        discovery_candidate_detail,
        name="discovery_candidate_detail",
    ),
    path("discovery/candidates/action/", discovery_candidates_action, name="discovery_candidates_action"),
]
