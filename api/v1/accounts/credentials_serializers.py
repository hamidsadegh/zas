from rest_framework import serializers

from accounts.models import (
    SiteCredential,
    SSHCredential,
    SNMPCredential,
    HTTPCredential,
)


class SiteCredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteCredential
        fields = "__all__"


class SSHCredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = SSHCredential
        fields = "__all__"


class SNMPCredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = SNMPCredential
        fields = "__all__"


class HTTPCredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = HTTPCredential
        fields = "__all__"
