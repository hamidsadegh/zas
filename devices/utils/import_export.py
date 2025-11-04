import pandas as pd # pyright: ignore[reportMissingModuleSource, reportMissingImports]
from io import BytesIO
from django.http import HttpResponse
from devices.models import Device, Organization, Area, Vendor, Platform, DeviceType, DeviceRole


def export_devices_to_excel(request):
    df = pd.DataFrame(Device.objects.values())
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)

    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=devices_export.xlsx'
    return response


# For now not activated in admin actions
def import_devices_from_excel(filepath):
    """Import devices from Excel file (must match expected columns)."""
    df = pd.read_excel(filepath)
    for _, row in df.iterrows():
        Device.objects.get_or_create(
            name=row["name"],
            management_ip=row["management_ip"],
            status=row.get("status", "active"),
            organization=Organization.objects.get_or_create(name=row["organization__name"])[0],
            area=Area.objects.get_or_create(name=row["area__name"])[0],
            vendor=Vendor.objects.get_or_create(name=row["vendor__name"])[0],
            platform=Platform.objects.get_or_create(name=row["platform__name"])[0],
            device_type=DeviceType.objects.get_or_create(model=row["device_type__model"])[0],
        )
