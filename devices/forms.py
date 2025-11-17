from django import forms

from accounts.models import SystemSettings


class SystemSettingsForm(forms.ModelForm):
    class Meta:
        model = SystemSettings
        fields = [
            "tacacs_enabled",
            "tacacs_server_ip",
            "tacacs_port",
            "tacacs_key",
            "tacacs_authorization_service",
            "tacacs_retries",
            "tacacs_session_timeout",
            "tacacs_admin_group",
            "tacacs_superuser_group",
            "allow_local_superusers",
        ]
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
            "allow_local_superusers": forms.CheckboxInput(),
        }
