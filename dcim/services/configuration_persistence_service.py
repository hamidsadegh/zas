# dcim/services/configuration_persistence_service.py

import hashlib
from django.utils import timezone

from dcim.models import DeviceConfiguration


class ConfigurationPersistenceService:
    @staticmethod
    def normalize(config_text: str) -> str:
        """
        Normalize configuration by removing volatile lines.
        """
        lines = []
        for line in config_text.splitlines():
            if line.startswith("! Last configuration change"):
                continue
            lines.append(line.rstrip())
        return "\n".join(lines).strip()

    @staticmethod
    def hash_config(config_text: str) -> str:
        return hashlib.sha256(config_text.encode()).hexdigest()

    @classmethod
    def persist(
        cls,
        *,
        device,
        config_text,
        source,
        collected_by=None,
        success=True,
        error_message=None,
    ) -> DeviceConfiguration | None:
        """
        Persist a configuration only if it has changed.
        Returns the new DeviceConfiguration or None if unchanged.
        """

        if not success:
            return DeviceConfiguration.objects.create(
                device=device,
                collected_at=timezone.now(),
                config_text="",
                source=source,
                success=False,
                error_message=error_message,
            )

        normalized = cls.normalize(config_text)
        cfg_hash = cls.hash_config(normalized)

        latest = (
            DeviceConfiguration.objects
            .filter(device=device)
            .order_by("-collected_at")
            .first()
        )

        if latest and latest.config_hash == cfg_hash:
            return None  # No change → no new row

        return DeviceConfiguration.objects.create(
            device=device,
            collected_at=timezone.now(),
            config_text=normalized,
            source=source,
            collected_by=collected_by,
            config_hash=cfg_hash,
            previous=latest,
            success=True,
        )
