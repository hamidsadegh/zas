'''
Here we define validation services for ensuring data integrity globally.
'''


from django.core.exceptions import ValidationError


INVALID_SERIAL_VALUES = {"N/A", "UNKNOWN", "N"}


def normalize_serial_number(value):
    if value is None:
        return None
    serial = str(value).strip()
    if not serial:
        return None
    serial_upper = serial.upper()
    if serial_upper in INVALID_SERIAL_VALUES or serial_upper.startswith("UNKNOWN:"):
        return None
    return serial


def validate_device(device):
    """Run device validations that used to live on the model."""
    validate_device_rack_area(device, device.rack, device.area)


def validate_device_rack_area(device, rack, area):
    """Ensure the rack belongs to the provided area before saving a device."""
    if rack and not area:
        raise ValidationError({"rack": "Select an area before choosing a rack."})
    if rack and area and rack.area_id != getattr(area, "id", None):
        raise ValidationError({"rack": "Selected rack does not belong to the chosen area."})


def validate_device_serial_uniqueness(device):
    from asset.models import InventoryItem
    from dcim.models import Device, DeviceModule

    serial = normalize_serial_number(getattr(device, "serial_number", None))
    device.serial_number = serial
    if not serial:
        return

    serial_filter = {"serial_number__iexact": serial}

    duplicate_device = Device.objects.filter(**serial_filter).exclude(pk=device.pk).first()
    if duplicate_device:
        raise ValidationError(
            {"serial_number": f"Serial number already exists on device '{duplicate_device.name}'."}
        )

    duplicate_module = DeviceModule.objects.select_related("device").filter(**serial_filter).first()
    if duplicate_module:
        raise ValidationError(
            {
                "serial_number": (
                    "Serial number already exists on production module "
                    f"'{duplicate_module.name}' of device '{duplicate_module.device.name}'."
                )
            }
        )

    duplicate_storage = InventoryItem.objects.filter(**serial_filter).first()
    if duplicate_storage:
        raise ValidationError(
            {
                "serial_number": (
                    "Serial number already exists in storage inventory "
                    f"('{duplicate_storage.designation}')."
                )
            }
        )


def validate_device_module_serial_uniqueness(module):
    from asset.models import InventoryItem
    from dcim.models import Device, DeviceModule

    serial = normalize_serial_number(getattr(module, "serial_number", None))
    module.serial_number = serial
    if not serial:
        return

    serial_filter = {"serial_number__iexact": serial}

    duplicate_module_qs = DeviceModule.objects.select_related("device").filter(**serial_filter)
    if module.pk:
        duplicate_module_qs = duplicate_module_qs.exclude(pk=module.pk)
    duplicate_module = duplicate_module_qs.first()
    if duplicate_module:
        raise ValidationError(
            {
                "serial_number": (
                    "Serial number already exists on production module "
                    f"'{duplicate_module.name}' of device '{duplicate_module.device.name}'."
                )
            }
        )

    duplicate_device = Device.objects.filter(**serial_filter).first()
    if duplicate_device:
        raise ValidationError(
            {"serial_number": f"Serial number already exists on device '{duplicate_device.name}'."}
        )

    duplicate_storage = InventoryItem.objects.filter(**serial_filter).first()
    if duplicate_storage:
        raise ValidationError(
            {
                "serial_number": (
                    "Serial number already exists in storage inventory "
                    f"('{duplicate_storage.designation}')."
                )
            }
        )


def validate_inventory_item_serial_uniqueness(item):
    from asset.models import InventoryItem
    from dcim.models import Device, DeviceModule

    serial = normalize_serial_number(getattr(item, "serial_number", None))
    item.serial_number = serial
    if not serial:
        return

    serial_filter = {"serial_number__iexact": serial}

    duplicate_device = Device.objects.filter(**serial_filter).first()
    if duplicate_device:
        raise ValidationError(
            {"serial_number": f"Serial number already exists in Production device '{duplicate_device.name}'."}
        )

    duplicate_module = DeviceModule.objects.select_related("device").filter(**serial_filter).first()
    if duplicate_module:
        raise ValidationError(
            {
                "serial_number": (
                    "Serial number already exists in Production module "
                    f"'{duplicate_module.name}' of device '{duplicate_module.device.name}'."
                )
            }
        )

    duplicate_storage_qs = InventoryItem.objects.filter(**serial_filter)
    if item.pk:
        duplicate_storage_qs = duplicate_storage_qs.exclude(pk=item.pk)
    if duplicate_storage_qs.exists():
        raise ValidationError({"serial_number": "Serial number already exists in Storage inventory."})
