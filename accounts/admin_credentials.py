from django import forms
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
    class SSHCredentialAdminForm(forms.ModelForm):
        ssh_password = forms.CharField(
            widget=forms.PasswordInput(render_value=False),
            required=False,
            help_text="Leave blank to keep the existing password.",
        )

        class Meta:
            model = SSHCredential
            fields = "__all__"

        def clean_ssh_password(self):
            value = self.cleaned_data.get("ssh_password")
            if self.instance.pk and not value:
                return self.instance.ssh_password
            if not value:
                raise forms.ValidationError("This field is required.")
            return value

    form = SSHCredentialAdminForm
    list_display = ("name", "site", "ssh_username", "ssh_port")
    autocomplete_fields = ("site",)


@admin.register(SNMPCredential)
class SNMPCredentialAdmin(admin.ModelAdmin):
    class SNMPCredentialAdminForm(forms.ModelForm):
        snmp_community = forms.CharField(
            widget=forms.PasswordInput(render_value=False),
            required=False,
            help_text="Leave blank to keep the existing community.",
        )
        snmp_auth_key = forms.CharField(
            widget=forms.PasswordInput(render_value=False),
            required=False,
            help_text="Leave blank to keep the existing auth key.",
        )
        snmp_priv_key = forms.CharField(
            widget=forms.PasswordInput(render_value=False),
            required=False,
            help_text="Leave blank to keep the existing privacy key.",
        )

        class Meta:
            model = SNMPCredential
            fields = "__all__"

        def _preserve_if_blank(self, field_name):
            value = self.cleaned_data.get(field_name)
            if self.instance.pk and not value:
                return getattr(self.instance, field_name)
            return value

        def clean_snmp_community(self):
            return self._preserve_if_blank("snmp_community")

        def clean_snmp_auth_key(self):
            return self._preserve_if_blank("snmp_auth_key")

        def clean_snmp_priv_key(self):
            return self._preserve_if_blank("snmp_priv_key")

    form = SNMPCredentialAdminForm
    list_display = ("name", "site", "snmp_version", "snmp_port")
    autocomplete_fields = ("site",)


@admin.register(HTTPCredential)
class HTTPCredentialAdmin(admin.ModelAdmin):
    class HTTPCredentialAdminForm(forms.ModelForm):
        http_password = forms.CharField(
            widget=forms.PasswordInput(render_value=False),
            required=False,
            help_text="Leave blank to keep the existing password.",
        )
        http_token = forms.CharField(
            widget=forms.PasswordInput(render_value=False),
            required=False,
            help_text="Leave blank to keep the existing token.",
        )

        class Meta:
            model = HTTPCredential
            fields = "__all__"

        def _preserve_if_blank(self, field_name):
            value = self.cleaned_data.get(field_name)
            if self.instance.pk and not value:
                return getattr(self.instance, field_name)
            return value

        def clean_http_password(self):
            return self._preserve_if_blank("http_password")

        def clean_http_token(self):
            return self._preserve_if_blank("http_token")

    form = HTTPCredentialAdminForm
    list_display = ("name", "site", "http_base_url", "http_port", "http_verify_tls")
    autocomplete_fields = ("site",)
