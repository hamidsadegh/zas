from django.urls import path, include

urlpatterns = [
    path("automation/", include("api.v1.automation.urls")),
    path("accounts/", include("api.v1.accounts.urls")),
    path("dcim/", include("api.v1.dcim.urls")),
]
 