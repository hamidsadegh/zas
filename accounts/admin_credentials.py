from django.contrib import admin

from accounts.models import (
    SiteCredential,
    SSHCredential,
    SNMPCredential,
    HTTPCredential,
)


@admin.register(SiteCredential)
class SiteCredentialAdmin(admin.ModelAdmin):
    list_display = ("name", "site", "type", "created_at")
    list_filter = ("type", "site")
    search_fields = ("name",)


@admin.register(SSHCredential)
class SSHCredentialAdmin(admin.ModelAdmin):
    list_display = ("name", "site", "ssh_username", "ssh_port")
    autocomplete_fields = ("site",)


@admin.register(SNMPCredential)
class SNMPCredentialAdmin(admin.ModelAdmin):
    list_display = ("name", "site", "snmp_version", "snmp_port")
    autocomplete_fields = ("site",)


@admin.register(HTTPCredential)
class HTTPCredentialAdmin(admin.ModelAdmin):
    list_display = ("name", "site", "http_base_url", "http_port", "http_verify_tls")
    autocomplete_fields = ("site",)
