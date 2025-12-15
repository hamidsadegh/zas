# automation/platform.py

from dcim.choices import DevicePlatformChoices
from dcim.models import Device


class PlatformResolutionError(RuntimeError):
    pass


def resolve_platform(device: Device) -> str:
    """
    Resolve the automation platform for a device.
    Single source of truth for all automation engines.
    """
    if not device.device_type:
        raise PlatformResolutionError(
            f"Device {device} has no device type"
        )

    platform = device.device_type.platform
    if not platform:
        return DevicePlatformChoices.UNKNOWN

    return platform
