from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from netaddr import EUI, AddrFormatError, mac_unix_expanded, eui64_unix_expanded


__all__ = (
    "MACAddressField",
    "WWNField",
)


class mac_unix_expanded_uppercase(mac_unix_expanded):
    word_fmt = '%.2X'


class eui64_unix_expanded_uppercase(eui64_unix_expanded):
    word_fmt = '%.2X'


#
# Fields
#

class MACAddressField(models.Field):
    description = 'PostgreSQL MAC Address field'

    def python_type(self):
        return EUI

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def get_internal_type(self):
        return 'CharField'

    def to_python(self, value):
        if value is None:
            return value
        if type(value) is str:
            value = value.replace(' ', '')
        try:
            return EUI(value, version=48, dialect=mac_unix_expanded_uppercase)
        except AddrFormatError:
            raise ValidationError(_("Invalid MAC address format: {value}").format(value=value))

    def db_type(self, connection):
        return 'macaddr'

    def get_prep_value(self, value):
        if not value:
            return None
        return str(self.to_python(value))


class WWNField(models.Field):
    description = 'World Wide Name field'

    def python_type(self):
        return EUI

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def get_internal_type(self):
        return 'CharField'

    def to_python(self, value):
        if value is None:
            return value
        try:
            return EUI(value, version=64, dialect=eui64_unix_expanded_uppercase)
        except AddrFormatError:
            raise ValidationError(_("Invalid WWN format: {value}").format(value=value))

    def db_type(self, connection):
        return 'macaddr8'

    def get_prep_value(self, value):
        if not value:
            return None
        return str(self.to_python(value))
