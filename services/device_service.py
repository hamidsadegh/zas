from services.validation_service import validate_device_rack_area


def validate_device(device):
    """Run device validations that used to live on the model."""
    validate_device_rack_area(device, device.rack, device.area)
