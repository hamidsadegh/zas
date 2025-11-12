# accounts/admin.py
from django.contrib import admin
from .models import SystemSettings


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "tacacs_enabled",
        "tacacs_server_ip",
        "tacacs_port",
        "updated_at",
    )
