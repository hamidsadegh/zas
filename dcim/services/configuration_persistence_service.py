# dcim/services/configuration_persistence_service.py

from django.utils import timezone
from dcim.models import DeviceConfiguration


class ConfigurationPersistenceService:
    @staticmethod
    def persist(*, device, config_text, source, success=True, error_message=None):
        """
        Persist a device configuration backup into DCIM.
        """
        return DeviceConfiguration.objects.create(
            device=device,
            backup_time=timezone.now(),
            config_text=config_text,
            source=source,
            success=success,
            error_message=error_message,
        )
