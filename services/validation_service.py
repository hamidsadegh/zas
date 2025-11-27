from django.core.exceptions import ValidationError


def validate_device_rack_area(device, rack, area):
    """Ensure the rack belongs to the provided area before saving a device."""
    if rack and not area:
        raise ValidationError({"rack": "Select an area before choosing a rack."})
    if rack and area and rack.area_id != getattr(area, "id", None):
        raise ValidationError({"rack": "Selected rack does not belong to the chosen area."})
