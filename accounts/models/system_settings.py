from django.db import models
from encrypted_model_fields.fields import EncryptedCharField


# -----------------------
# Manager ensuring singleton behavior
# -----------------------
class SystemSettingsManager(models.Manager):
    def load(self):
        obj, _ = self.get_or_create(id=1)
        return obj


# -----------------------
# SYSTEM SETTINGS (Singleton)
# -----------------------
class SystemSettings(models.Model):

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)

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
        "reachability_netconf_enabled",
        "reachability_interval_minutes",
    )

    ALLOW_LOCAL_SUPERUSERS = ("allow_local_superusers",)

    # ---------------- TACACS ----------------
    tacacs_enabled = models.BooleanField(default=False)
    tacacs_server_ip = models.GenericIPAddressField(protocol="IPv4", blank=True, null=True)
    tacacs_port = models.PositiveIntegerField(default=49)
    tacacs_key = EncryptedCharField(max_length=255, blank=True, null=True)
    tacacs_authorization_service = models.CharField(max_length=100, blank=True, null=True)
    tacacs_retries = models.PositiveSmallIntegerField(default=3)
    tacacs_session_timeout = models.PositiveIntegerField(default=60)
    tacacs_admin_group = models.CharField(max_length=100, blank=True, null=True)
    tacacs_superuser_group = models.CharField(max_length=100, blank=True, null=True)

    allow_local_superusers = models.BooleanField(default=True)

    # ---------------- Reachability ----------------
    reachability_ping_enabled = models.BooleanField(default=True)
    reachability_snmp_enabled = models.BooleanField(default=True)
    reachability_ssh_enabled = models.BooleanField(default=False)
    reachability_netconf_enabled = models.BooleanField(default=False)
    reachability_interval_minutes = models.PositiveIntegerField(default=10)
    reachability_last_run = models.DateTimeField(blank=True, null=True)

    updated_at = models.DateTimeField(auto_now=True)

    # ---------------- Manager (Singleton) ----------------
    objects = SystemSettingsManager()

    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"

    def __str__(self):
        return "System Settings"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def get_reachability_checks(self):
        return {
            "ping": bool(self.reachability_ping_enabled),
            "snmp": bool(self.reachability_snmp_enabled),
            "ssh": bool(self.reachability_ssh_enabled),
            "netconf": bool(self.reachability_netconf_enabled),
        }
