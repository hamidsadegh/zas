from django.urls import path
from . import views
from . import organization_views
from .views import debug_session

urlpatterns = [
    path("", views.home, name="dashboard"),
    # TEMP URL for testing
    path("debug-session/", debug_session, name="debug-session"),
    # TEMP END
    path("organization/", organization_views.OrganizationHomeView.as_view(), name="organization_home"),
    path("organization/org/<uuid:org_id>/update/", organization_views.organization_update, name="organization_update"),
    path("organization/sites/create/", organization_views.site_create, name="organization_site_create"),
    path("organization/sites/<uuid:site_id>/", organization_views.site_detail, name="organization_site_detail"),
    path("organization/sites/<uuid:site_id>/edit/", organization_views.site_edit_form, name="organization_site_edit_form"),
    path("organization/sites/<uuid:site_id>/update/", organization_views.site_update, name="organization_site_update"),
    path("organization/sites/<uuid:site_id>/delete/", organization_views.site_delete, name="organization_site_delete"),
    path("organization/areas/create/", organization_views.area_create, name="organization_area_create"),
    path("organization/areas/<uuid:area_id>/update/", organization_views.area_update, name="organization_area_update"),
    path("organization/areas/<uuid:area_id>/delete/", organization_views.area_delete, name="organization_area_delete"),
    path("organization/racks/create/", organization_views.rack_create, name="organization_rack_create"),
    path("organization/racks/<uuid:rack_id>/update/", organization_views.rack_update, name="organization_rack_update"),
    path("organization/racks/<uuid:rack_id>/delete/", organization_views.rack_delete, name="organization_rack_delete"),
]
