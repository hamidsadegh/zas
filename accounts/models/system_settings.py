from django.db import models
from encrypted_model_fields.fields import EncryptedCharField


class SystemSettings(models.Model):
    # Field groupings for forms/admin reuse
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
    SNMP_FIELDS = (
        "snmp_version",
        "snmp_port",
        "snmp_community",
        "snmp_security_level",
        "snmp_username",
        "snmp_auth_protocol",
        "snmp_auth_key",
        "snmp_priv_protocol",
        "snmp_priv_key",
    )
    OTHER_FIELDS = ("allow_local_superusers",)

    SNMP_VERSION_CHOICES = (
        ("v2c", "SNMPv2c"),
        ("v3", "SNMPv3"),
    )
    SNMP_SECURITY_LEVEL_CHOICES = (
        ("noAuthNoPriv", "noAuthNoPriv"),
        ("authNoPriv", "authNoPriv"),
        ("authPriv", "authPriv"),
    )
    SNMP_AUTH_PROTOCOL_CHOICES = (
        ("md5", "MD5"),
        ("sha", "SHA"),
    )
    SNMP_PRIV_PROTOCOL_CHOICES = (
        ("des", "DES"),
        ("aes128", "AES-128"),
    )

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
    reachability_ping_enabled = models.BooleanField(default=True)
    reachability_snmp_enabled = models.BooleanField(default=True)
    reachability_ssh_enabled = models.BooleanField(default=False)
    reachability_netconf_enabled = models.BooleanField(default=False)
    reachability_interval_minutes = models.PositiveIntegerField(default=10)
    reachability_last_run = models.DateTimeField(blank=True, null=True)
    snmp_version = models.CharField(
        max_length=5, choices=SNMP_VERSION_CHOICES, default="v2c"
    )
    snmp_port = models.PositiveIntegerField(default=161)
    snmp_community = models.CharField(max_length=128, blank=True, default="public")
    snmp_security_level = models.CharField(
        max_length=20, choices=SNMP_SECURITY_LEVEL_CHOICES, default="noAuthNoPriv"
    )
    snmp_username = models.CharField(max_length=128, blank=True, default="")
    snmp_auth_protocol = models.CharField(
        max_length=20,
        choices=SNMP_AUTH_PROTOCOL_CHOICES,
        blank=True,
        default="sha",
    )
    snmp_auth_key = EncryptedCharField(max_length=255, blank=True, null=True)
    snmp_priv_protocol = models.CharField(
        max_length=20,
        choices=SNMP_PRIV_PROTOCOL_CHOICES,
        blank=True,
        default="aes128",
    )
    snmp_priv_key = EncryptedCharField(max_length=255, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"

    def __str__(self):
        return "System Settings"

    # -----------------------
    # Helper APIs
    # -----------------------
    @classmethod
    def get(cls):
        """
        Return the singleton SystemSettings row, creating it with pk=1 when missing.
        """
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def get_reachability_checks(self):
        """
        Return the enabled/disabled state for reachability probes.
        """
        return {
            "ping": bool(self.reachability_ping_enabled),
            "snmp": bool(self.reachability_snmp_enabled),
            "ssh": bool(self.reachability_ssh_enabled),
            "netconf": bool(self.reachability_netconf_enabled),
        }

    def get_snmp_config(self):
        """
        Return SNMP configuration dict normalized for consumers.
        """
        return {
            "version": self.snmp_version or "v2c",
            "port": self.snmp_port or 161,
            "community": (self.snmp_community or "public").strip() or "public",
            "security_level": self.snmp_security_level or "noAuthNoPriv",
            "username": (self.snmp_username or "").strip(),
            "auth_protocol": self.snmp_auth_protocol or "",
            "auth_key": self.snmp_auth_key or "",
            "priv_protocol": self.snmp_priv_protocol or "",
            "priv_key": self.snmp_priv_key or "",
        }
