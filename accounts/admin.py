# accounts/admin.py
from django.contrib import admin

from accounts.models.system_settings import SystemSettings
from .admin_credentials import *  # noqa


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "tacacs_enabled",
        "tacacs_server_ip",
        "tacacs_port",
        "allow_local_superusers",
        "reachability_interval_minutes",
        "reachability_ping_enabled",
        "updated_at",
    )
    readonly_fields = ("reachability_last_run", "updated_at")
    fieldsets = (
        (
            "TACACS+ Settings",
            {
                "fields": SystemSettings.TACACS_FIELDS,
                "description": "Authentication server configuration.",
            },
        ),
        (
            "Reachability Settings",
            {
                "fields": SystemSettings.REACHABILITY_FIELDS
                + ("reachability_last_run",),
                "description": "Periodic device checks.",
            },
        ),
        (
            "Other Settings",
            {
                "fields": SystemSettings.ALLOW_LOCAL_SUPERUSERS + ("updated_at",),
                "description": "Miscellaneous and future settings.",
            },
        ),
    )

    # Prevent addition of multiple instances
    def has_add_permission(self, request):
        return False

