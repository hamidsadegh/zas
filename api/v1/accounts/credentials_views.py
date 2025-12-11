from rest_framework import viewsets

from accounts.models import (
    SiteCredential,
    SSHCredential,
    SNMPCredential,
    HTTPCredential,
)
from .credentials_serializers import (
    SiteCredentialSerializer,
    SSHCredentialSerializer,
    SNMPCredentialSerializer,
    HTTPCredentialSerializer,
)


class SiteCredentialViewSet(viewsets.ModelViewSet):
    queryset = SiteCredential.objects.all()
    serializer_class = SiteCredentialSerializer


class SSHCredentialViewSet(viewsets.ModelViewSet):
    queryset = SSHCredential.objects.all()
    serializer_class = SSHCredentialSerializer


class SNMPCredentialViewSet(viewsets.ModelViewSet):
    queryset = SNMPCredential.objects.all()
    serializer_class = SNMPCredentialSerializer


class HTTPCredentialViewSet(viewsets.ModelViewSet):
    queryset = HTTPCredential.objects.all()
    serializer_class = HTTPCredentialSerializer
