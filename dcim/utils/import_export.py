import pandas as pd # pyright: ignore[reportMissingModuleSource, reportMissingImports]
from io import BytesIO
from django.http import HttpResponse
from dcim.models import Area, Device, DeviceRole, DeviceType, Organization, Site, Vendor


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
        organization = Organization.objects.get_or_create(name=row["organization__name"])[0]
        site_name = row.get("site__name") or "Default"
        site = Site.objects.get_or_create(
            organization=organization,
            name=site_name,
        )[0]
        area = None
        area_name = row.get("area__name")
        if area_name:
            area, _ = Area.objects.get_or_create(
                name=area_name,
                site=site,
            )
        Device.objects.get_or_create(
            name=row["name"],
            management_ip=row["management_ip"],
            status=row.get("status", "active"),
            site=site,
            area=area,
            vendor=Vendor.objects.get_or_create(name=row["vendor__name"])[0],
            device_type=DeviceType.objects.get_or_create(model=row["device_type__model"])[0],
            device_role=DeviceRole.objects.get_or_create(name=row["device_role__name"])[0],
        )
