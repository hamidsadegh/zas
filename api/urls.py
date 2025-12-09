from django.urls import path, include

urlpatterns = [
    path("", include("api.v1.urls")),   # This allows /api/ → /api/v1/
    path("v1/", include("api.v1.urls")),
]
