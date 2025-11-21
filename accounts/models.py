from django.db import models


class SystemSettings(models.Model):
    TACACS_FIELDS = (
        "tacacs_enabled",
        "tacacs_server_ip",
        "tacacs_port",
        "tacacs_key",
        "tacacs_authorization_service",
        "tacacs_retries",
        "tacacs_session_timeout",
        "tacacs_admin_group",
        "tacacs_superuser_group",
    )
    REACHABILITY_FIELDS = (
        "reachability_ping_enabled",
        "reachability_snmp_enabled",
        "reachability_ssh_enabled",
        "reachability_telemetry_enabled",
        "reachability_interval_minutes",
    )
    OTHER_FIELDS = ("allow_local_superusers",)

    tacacs_enabled = models.BooleanField(default=False)
    tacacs_server_ip = models.GenericIPAddressField(protocol="IPv4", blank=True, null=True)
    tacacs_port = models.PositiveIntegerField(default=49)
    tacacs_key = models.CharField(max_length=255, blank=True, null=True)
    tacacs_authorization_service = models.CharField(max_length=100, blank=True, null=True)
    tacacs_retries = models.PositiveSmallIntegerField(default=3)
    tacacs_session_timeout = models.PositiveIntegerField(default=60)
    tacacs_admin_group = models.CharField(max_length=100, blank=True, null=True)
    tacacs_superuser_group = models.CharField(max_length=100, blank=True, null=True)
    allow_local_superusers = models.BooleanField(default=True)
    reachability_ping_enabled = models.BooleanField(default=True)
    reachability_snmp_enabled = models.BooleanField(default=True)
    reachability_ssh_enabled = models.BooleanField(default=False)
    reachability_telemetry_enabled = models.BooleanField(default=False)
    reachability_interval_minutes = models.PositiveIntegerField(default=10)
    reachability_last_run = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"

    def __str__(self):
        return "System Settings"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @classmethod
    def section_fields(cls, section):
        mapping = {
            "tacacs": cls.TACACS_FIELDS,
            "reachability": cls.REACHABILITY_FIELDS,
            "other": cls.OTHER_FIELDS,
        }
        return mapping.get(section, ())

    def get_reachability_checks(self):
        return {
            "ping": self.reachability_ping_enabled,
            "snmp": self.reachability_snmp_enabled,
            "ssh": self.reachability_ssh_enabled,
            "telemetry": self.reachability_telemetry_enabled,
        }

    def reachability_checks_enabled(self):
        return any(self.get_reachability_checks().values())
