from django.db import models


class SystemSettings(models.Model):
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
