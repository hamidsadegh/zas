# accounts/admin.py
from django.contrib import admin
from accounts.models.site_credentials import SiteCredential
from accounts.models.system_settings import SystemSettings


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
                + SystemSettings.SNMP_FIELDS
                + ("reachability_last_run",),
                "description": "Periodic device checks.",
            },
        ),
        (
            "Other Settings",
            {
                "fields": SystemSettings.OTHER_FIELDS + ("updated_at",),
                "description": "Miscellaneous and future settings.",
            },
        ),
    )


@admin.register(SiteCredential)
class SiteCredentialAdmin(admin.ModelAdmin):
    list_display = ("site", "ssh_username", "ssh_port")
    search_fields = ("site__name", "ssh_username")
