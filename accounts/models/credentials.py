import uuid

from django.db import models
from encrypted_model_fields.fields import EncryptedCharField
from django.utils import timezone

from dcim.models import Site


class SiteCredential(models.Model):
    """
    Base credential model. Each subclass (SSH, SNMP, HTTP) contains actual fields.
    """

    CRED_TYPE = (
        ("ssh", "SSH"),
        ("snmp", "SNMP"),
        ("http", "HTTP/HTTPS"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name="credentials",
    )
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=CRED_TYPE)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Credential"
        verbose_name_plural = "Credentials"

    def __str__(self):
        return f"{self.site.name} / {self.name} ({self.type})"


class SSHCredential(SiteCredential):
    ssh_username = models.CharField(max_length=100)
    ssh_password = EncryptedCharField(max_length=500)
    ssh_port = models.PositiveSmallIntegerField(default=22)

    class Meta:
        verbose_name = "SSH Credential"
        verbose_name_plural = "SSH Credentials"


class SNMPCredential(SiteCredential):
    snmp_version = models.CharField(max_length=10, default="v2c")
    snmp_port = models.PositiveSmallIntegerField(default=161)

    snmp_community = EncryptedCharField(max_length=200, blank=True, null=True)

    # SNMPv3
    snmp_security_level = models.CharField(max_length=20, blank=True, null=True)
    snmp_username = models.CharField(max_length=100, blank=True, null=True)
    snmp_auth_protocol = models.CharField(max_length=50, blank=True, null=True)
    snmp_auth_key = EncryptedCharField(max_length=500, blank=True, null=True)
    snmp_priv_protocol = models.CharField(max_length=50, blank=True, null=True)
    snmp_priv_key = EncryptedCharField(max_length=500, blank=True, null=True)

    class Meta:
        verbose_name = "SNMP Credential"
        verbose_name_plural = "SNMP Credentials"


class HTTPCredential(SiteCredential):
    http_username = models.CharField(max_length=100, blank=True, null=True)
    http_password = EncryptedCharField(max_length=500, blank=True, null=True)
    http_token = EncryptedCharField(max_length=500, blank=True, null=True)

    http_base_url = models.CharField(max_length=300, blank=True, null=True)
    http_port = models.PositiveSmallIntegerField(default=443)
    http_verify_tls = models.BooleanField(default=True)

    class Meta:
        verbose_name = "HTTP/HTTPS Credential"
        verbose_name_plural = "HTTP/HTTPS Credentials"
