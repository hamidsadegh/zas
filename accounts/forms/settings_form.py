from django import forms

from accounts.models.system_settings import SystemSettings
from accounts.choices import REACHABILITY_INTERVAL_CHOICES


class BaseSystemSettingsForm(forms.ModelForm):
    """Base form that only writes the fields in this section."""

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            update_fields = list(self.Meta.fields)
            # Ensure auto_now timestamp updates with partial saves
            if "updated_at" not in update_fields:
                update_fields.append("updated_at")
            instance.save(update_fields=update_fields)
        return instance


class TacacsSettingsForm(BaseSystemSettingsForm):
    class Meta:
        model = SystemSettings
        fields = SystemSettings.TACACS_FIELDS
        widgets = {
            "tacacs_enabled": forms.CheckboxInput(attrs={"class": "toggle-input"}),
            "tacacs_server_ip": forms.TextInput(attrs={"placeholder": "10.10.10.10"}),
            "tacacs_port": forms.NumberInput(attrs={"min": 1, "max": 65535}),
            "tacacs_key": forms.PasswordInput(
                attrs={"placeholder": "shared secret", "class": "password-field"},
                render_value=True,
            ),
            "tacacs_authorization_service": forms.TextInput(
                attrs={"placeholder": "system-services"}
            ),
            "tacacs_retries": forms.NumberInput(attrs={"min": 0, "max": 10}),
            "tacacs_session_timeout": forms.NumberInput(attrs={"min": 10, "max": 3600}),
            "tacacs_admin_group": forms.TextInput(attrs={"placeholder": "ise-admins"}),
            "tacacs_superuser_group": forms.TextInput(attrs={"placeholder": "ise-superusers"}),
        }


class ReachabilitySettingsForm(BaseSystemSettingsForm):
    class Meta:
        model = SystemSettings
        fields = SystemSettings.REACHABILITY_FIELDS + SystemSettings.SNMP_FIELDS
        widgets = {
            "reachability_ping_enabled": forms.CheckboxInput(),
            "reachability_snmp_enabled": forms.CheckboxInput(),
            "reachability_ssh_enabled": forms.CheckboxInput(),
            "reachability_netconf_enabled": forms.CheckboxInput(),
            "reachability_interval_minutes": forms.Select(
                choices=REACHABILITY_INTERVAL_CHOICES
            ),
            "snmp_version": forms.Select(),
            "snmp_port": forms.NumberInput(attrs={"min": 1, "max": 65535}),
            "snmp_community": forms.TextInput(attrs={"placeholder": "public"}),
            "snmp_security_level": forms.Select(),
            "snmp_username": forms.TextInput(attrs={"placeholder": "snmp-user"}),
            "snmp_auth_protocol": forms.Select(),
            "snmp_auth_key": forms.PasswordInput(
                attrs={"placeholder": "auth passphrase"}, render_value=True
            ),
            "snmp_priv_protocol": forms.Select(),
            "snmp_priv_key": forms.PasswordInput(
                attrs={"placeholder": "privacy passphrase"}, render_value=True
            ),
        }


class OtherSettingsForm(BaseSystemSettingsForm):
    class Meta:
        model = SystemSettings
        fields = SystemSettings.OTHER_FIELDS
        widgets = {
            "allow_local_superusers": forms.CheckboxInput(),
        }
